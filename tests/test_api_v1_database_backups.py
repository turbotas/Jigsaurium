import bz2
from datetime import datetime, timedelta, timezone
import gzip
import hashlib
from pathlib import Path
import time

import pytest

from app.database_backups import build_backup_filename, write_mysql_compatible_backup
from app.db import get_session
from app.models import AuditEvent, DatabaseBackup, Jigsaw, JigsawImage, Role, User, UserRole
from tests.image_fixtures import png_bytes


@pytest.fixture()
def seeded_backup_identity_data(app):
    with app.app_context():
        db_session = get_session()

        admin_role = db_session.query(Role).filter_by(name="administrator").one()
        member_role = db_session.query(Role).filter_by(name="member").one()

        admin_user = User(email="admin.backups@example.com", display_name="Admin Backups")
        member_user = User(email="member.backups@example.com", display_name="Member Backups")
        admin_user.set_password("AdminBackupsPass123!")
        member_user.set_password("MemberBackupsPass123!")

        db_session.add_all([admin_user, member_user])
        db_session.flush()
        db_session.add_all(
            [
                UserRole(user_id=admin_user.id, role_id=admin_role.id),
                UserRole(user_id=member_user.id, role_id=member_role.id),
            ]
        )

        jigsaw = Jigsaw(title="Backup Puzzle", piece_count=500)
        db_session.add(jigsaw)
        db_session.flush()
        db_session.add(
            JigsawImage(
                jigsaw_id=jigsaw.id,
                tag="Completed",
                filename="backup-image.png",
                mime_type="image/png",
                image_data=(png_bytes(b"\x89PNG\r\n\x1a\n") + (b"z" * 4096)),
                uploaded_by_user_id=admin_user.id,
            )
        )
        db_session.commit()

        seeded_ids = {
            "admin_email": admin_user.email,
            "admin_password": "AdminBackupsPass123!",
            "member_email": member_user.email,
            "member_password": "MemberBackupsPass123!",
        }

    db_session.remove()
    yield seeded_ids


def _login(client, *, email, password):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    payload = response.get_json()["data"]
    return {
        "csrf_token": payload["csrf_token"],
    }


def _wait_for_backup_completion(client, backup_id, *, timeout_seconds=10.0):
    deadline = time.monotonic() + timeout_seconds
    last_payload = None
    while time.monotonic() < deadline:
        list_response = client.get("/api/v1/system/database-backups")
        assert list_response.status_code == 200
        last_payload = list_response.get_json()["data"]
        match = next((entry for entry in last_payload if int(entry["id"]) == int(backup_id)), None)
        assert match is not None
        if match["status"] in {"completed", "failed"}:
            return match
        time.sleep(0.1)
    raise AssertionError(f"Backup {backup_id} did not complete in time. Last payload: {last_payload}")


@pytest.mark.functional
def test_database_backup_endpoints_require_admin_role(app, seeded_backup_identity_data):
    app.config["DB_BACKUP_STORAGE_PATH"] = str((Path(app.instance_path) / "backup-test-role").resolve())

    unauthenticated_list = app.test_client().get("/api/v1/system/database-backups")
    assert unauthenticated_list.status_code == 401

    unauthenticated_create = app.test_client().post(
        "/api/v1/system/database-backups",
        json={},
    )
    assert unauthenticated_create.status_code == 401

    member_client = app.test_client()
    member_login = _login(
        member_client,
        email=seeded_backup_identity_data["member_email"],
        password=seeded_backup_identity_data["member_password"],
    )

    forbidden_list = member_client.get("/api/v1/system/database-backups")
    assert forbidden_list.status_code == 403

    forbidden_create = member_client.post(
        "/api/v1/system/database-backups",
        headers={"X-CSRF-Token": member_login["csrf_token"]},
        json={},
    )
    assert forbidden_create.status_code == 403

    forbidden_download = member_client.get("/api/v1/system/database-backups/1/download")
    assert forbidden_download.status_code == 403

    forbidden_delete = member_client.delete(
        "/api/v1/system/database-backups/1",
        headers={"X-CSRF-Token": member_login["csrf_token"]},
    )
    assert forbidden_delete.status_code == 403


@pytest.mark.functional
def test_admin_can_create_list_and_download_mysql_compatible_database_backup(app, seeded_backup_identity_data, tmp_path):
    backup_root = tmp_path / "database_backups"
    app.config["DB_BACKUP_STORAGE_PATH"] = str(backup_root)
    app.config["DB_BACKUP_BLOB_CHUNK_BYTES"] = 64
    app.config["DB_BACKUP_MAX_STATEMENT_BYTES"] = 512 * 1024
    app.config["DB_BACKUP_COMPRESSION"] = "gzip"
    app.config["APP_ENV"] = "test"
    app.config["APP_VERSION"] = "1.2.3"

    client = app.test_client()
    login = _login(
        client,
        email=seeded_backup_identity_data["admin_email"],
        password=seeded_backup_identity_data["admin_password"],
    )

    create_response = client.post(
        "/api/v1/system/database-backups",
        headers={"X-CSRF-Token": login["csrf_token"]},
        json={},
    )
    assert create_response.status_code == 202
    create_payload = create_response.get_json()["data"]
    assert create_payload["status"] == "queued"
    assert create_payload["filename"].startswith("jigsaurium-test-v1.2.3-")
    assert create_payload["filename"].endswith(".sql.gz")

    completed_backup = _wait_for_backup_completion(client, create_payload["id"])
    assert completed_backup["status"] == "completed"
    assert int(completed_backup["file_size_bytes"] or 0) > 0
    assert completed_backup["download_url"] == f"/api/v1/system/database-backups/{create_payload['id']}/download"

    download_response = client.get(f"/api/v1/system/database-backups/{create_payload['id']}/download")
    assert download_response.status_code == 200
    assert download_response.headers.get("Content-Type", "").startswith("application/gzip")
    assert "attachment; filename=" in str(download_response.headers.get("Content-Disposition") or "")

    dump_sql = gzip.decompress(download_response.data).decode("utf-8")
    assert "SET FOREIGN_KEY_CHECKS=0;" in dump_sql
    assert "CREATE TABLE" in dump_sql
    assert "jigsaw_images" in dump_sql
    assert "INSERT INTO `jigsaw_images`" in dump_sql
    assert "UNHEX(" in dump_sql

    backup_files = list(backup_root.glob("*.sql.gz"))
    assert len(backup_files) == 1


@pytest.mark.functional
def test_admin_can_delete_completed_database_backup(app, seeded_backup_identity_data, tmp_path):
    backup_root = tmp_path / "database_backups_delete"
    app.config["DB_BACKUP_STORAGE_PATH"] = str(backup_root)
    app.config["DB_BACKUP_COMPRESSION"] = "gzip"

    client = app.test_client()
    login = _login(
        client,
        email=seeded_backup_identity_data["admin_email"],
        password=seeded_backup_identity_data["admin_password"],
    )

    create_response = client.post(
        "/api/v1/system/database-backups",
        headers={"X-CSRF-Token": login["csrf_token"]},
        json={},
    )
    assert create_response.status_code == 202
    created = create_response.get_json()["data"]

    completed_backup = _wait_for_backup_completion(client, created["id"])
    assert completed_backup["status"] == "completed"
    backup_path = backup_root / str(completed_backup["filename"])
    assert backup_path.exists()

    delete_response = client.delete(
        f"/api/v1/system/database-backups/{created['id']}",
        headers={"X-CSRF-Token": login["csrf_token"]},
    )
    assert delete_response.status_code == 200
    assert delete_response.get_json()["data"]["deleted"] is True

    list_response = client.get("/api/v1/system/database-backups")
    assert list_response.status_code == 200
    listed = list_response.get_json()["data"]
    assert all(int(entry["id"]) != int(created["id"]) for entry in listed)
    assert not backup_path.exists()


def _insert_backup_row(app, *, status, filename, backup_root, created_at, started_at=None, heartbeat_at=None):
    with app.app_context():
        db_session = get_session()
        backup_root.mkdir(parents=True, exist_ok=True)
        record = DatabaseBackup(
            filename=filename,
            storage_path=str((backup_root / filename).resolve()),
            file_format="mysql_sql",
            status=status,
            app_environment="test",
            app_version="1.0.0",
            created_at=created_at,
            started_at=started_at,
            heartbeat_at=heartbeat_at,
        )
        db_session.add(record)
        db_session.commit()
        record_id = int(record.id)
    db_session.remove()
    return record_id


@pytest.mark.functional
def test_stale_backups_are_marked_interrupted_and_can_be_deleted(app, seeded_backup_identity_data, tmp_path):
    backup_root = tmp_path / "database_backups_stale"
    app.config["DB_BACKUP_STORAGE_PATH"] = str(backup_root)
    app.config["DB_BACKUP_STALE_AFTER_SECONDS"] = 300
    now = datetime.now(timezone.utc)
    stale_running_id = _insert_backup_row(
        app,
        status="running",
        filename="stale-running.sql.gz",
        backup_root=backup_root,
        created_at=now - timedelta(days=5),
        started_at=now - timedelta(days=5),
        heartbeat_at=now - timedelta(minutes=10),
    )
    stale_queued_id = _insert_backup_row(
        app,
        status="queued",
        filename="stale-queued.sql.gz",
        backup_root=backup_root,
        created_at=now - timedelta(hours=1),
    )
    fresh_running_id = _insert_backup_row(
        app,
        status="running",
        filename="fresh-running.sql.gz",
        backup_root=backup_root,
        created_at=now - timedelta(hours=2),
        started_at=now - timedelta(hours=2),
        heartbeat_at=now - timedelta(seconds=20),
    )
    leftover_temp = backup_root / "stale-running.sql.gz.tmp"
    leftover_temp.write_bytes(b"partial")

    client = app.test_client()
    login = _login(
        client,
        email=seeded_backup_identity_data["admin_email"],
        password=seeded_backup_identity_data["admin_password"],
    )

    list_response = client.get("/api/v1/system/database-backups")
    assert list_response.status_code == 200
    by_id = {int(entry["id"]): entry for entry in list_response.get_json()["data"]}
    assert by_id[stale_running_id]["status"] == "failed"
    assert by_id[stale_running_id]["error_message"].startswith("Interrupted")
    assert by_id[stale_running_id]["completed_at"] is not None
    assert by_id[stale_queued_id]["status"] == "failed"
    assert by_id[fresh_running_id]["status"] == "running"
    assert by_id[fresh_running_id]["heartbeat_at"] is not None
    assert not leftover_temp.exists()

    with app.app_context():
        interrupted_events = (
            get_session().query(AuditEvent).filter_by(action="system.database_backup_interrupted").all()
        )
        assert {int(event.entity_id) for event in interrupted_events} == {stale_running_id, stale_queued_id}
        get_session().remove()

    delete_stale = client.delete(
        f"/api/v1/system/database-backups/{stale_running_id}",
        headers={"X-CSRF-Token": login["csrf_token"]},
    )
    assert delete_stale.status_code == 200

    delete_fresh = client.delete(
        f"/api/v1/system/database-backups/{fresh_running_id}",
        headers={"X-CSRF-Token": login["csrf_token"]},
    )
    assert delete_fresh.status_code == 409


@pytest.mark.functional
def test_backup_failure_after_database_error_is_recorded_and_temp_file_removed(
    app, seeded_backup_identity_data, tmp_path, monkeypatch
):
    import app.api.v1.routes as routes_module

    backup_root = tmp_path / "database_backups_failure"
    app.config["DB_BACKUP_STORAGE_PATH"] = str(backup_root)
    app.config["DB_BACKUP_COMPRESSION"] = "gzip"

    def failing_writer(*, output_path, **_kwargs):
        Path(output_path).write_bytes(b"partial")
        # Poison the job's session the way a database error mid-job would: a failed flush
        # leaves it needing a rollback before anything else can be committed.
        db_session = get_session()
        existing = db_session.query(DatabaseBackup).first()
        db_session.add(
            DatabaseBackup(
                filename=existing.filename,
                storage_path=existing.storage_path,
                file_format="mysql_sql",
                status="queued",
                app_environment="test",
                app_version="1.0.0",
            )
        )
        db_session.flush()

    monkeypatch.setattr(routes_module, "write_mysql_compatible_backup", failing_writer)

    client = app.test_client()
    login = _login(
        client,
        email=seeded_backup_identity_data["admin_email"],
        password=seeded_backup_identity_data["admin_password"],
    )
    create_response = client.post(
        "/api/v1/system/database-backups",
        headers={"X-CSRF-Token": login["csrf_token"]},
        json={},
    )
    assert create_response.status_code == 202
    created = create_response.get_json()["data"]

    finished = _wait_for_backup_completion(client, created["id"])
    assert finished["status"] == "failed"
    assert finished["error_message"]
    assert finished["download_url"] is None
    assert list(backup_root.glob("*.tmp")) == []
    assert list(backup_root.glob("*.sql.gz")) == []


@pytest.mark.parametrize("compression", ["gzip", "bzip2", "none"])
def test_streaming_backup_writer_reports_size_and_hash_of_written_file(app, seeded_backup_identity_data, tmp_path, compression):
    output_path = tmp_path / f"backup-{compression}.out"
    progress_calls = []
    with app.app_context():
        result = write_mysql_compatible_backup(
            output_path=output_path,
            engine=get_session().get_bind(),
            app_name="jigsaurium",
            app_env="test",
            app_version="1.0.0",
            generated_at=datetime(2026, 11, 23, 10, 0, tzinfo=timezone.utc),
            blob_chunk_bytes=64,
            max_statement_bytes=512 * 1024,
            compression=compression,
            on_progress=lambda: progress_calls.append(1),
        )
        get_session().remove()

    raw = output_path.read_bytes()
    assert result.file_size_bytes == len(raw)
    assert result.file_sha256 == hashlib.sha256(raw).hexdigest()
    if compression == "gzip":
        sql_text = gzip.decompress(raw).decode("utf-8")
    elif compression == "bzip2":
        sql_text = bz2.decompress(raw).decode("utf-8")
    else:
        sql_text = raw.decode("utf-8")
    assert sql_text.startswith("-- jigsaurium database backup\n")
    assert sql_text.endswith("SET FOREIGN_KEY_CHECKS=1;\n")
    assert "INSERT INTO `jigsaw_images`" in sql_text
    assert "SET @blob_jigsaw_images_1_0 = UNHEX(" in sql_text
    # One progress call per statement written (CREATE TABLE statements span several lines).
    assert 0 < len(progress_calls) <= sql_text.count("\n")


def test_backup_filename_does_not_double_the_version_prefix():
    generated_at = datetime(2026, 11, 18, 9, 3, 2, tzinfo=timezone.utc)
    filename = build_backup_filename(
        app_name="jigsaurium",
        app_env="dev",
        app_version="v0.2.30-2-g414577f",
        generated_at=generated_at,
        compression="gzip",
    )
    assert filename.startswith("jigsaurium-dev-v0.2.30-2-g414577f-")
    assert build_backup_filename(
        app_name="jigsaurium", app_env="dev", app_version="1.2.3", generated_at=generated_at, compression="gzip"
    ).startswith("jigsaurium-dev-v1.2.3-")
