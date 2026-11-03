import gzip
from pathlib import Path
import time

import pytest

from app.db import get_session
from app.models import Jigsaw, JigsawImage, Role, User, UserRole


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
                image_data=(b"\x89PNG\r\n\x1a\n" + (b"z" * 4096)),
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
