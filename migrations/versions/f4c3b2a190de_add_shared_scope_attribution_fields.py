"""add shared-scope attribution fields

Revision ID: f4c3b2a190de
Revises: 6b9d3e1f4a22
Create Date: 2026-10-19 12:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f4c3b2a190de"
down_revision: Union[str, Sequence[str], None] = "6b9d3e1f4a22"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _resolve_fallback_user_id(connection):
    admin_user_id = connection.execute(
        sa.text(
            """
            SELECT ur.user_id
            FROM user_roles ur
            JOIN roles r ON r.id = ur.role_id
            WHERE r.name = 'administrator'
            ORDER BY ur.user_id ASC
            LIMIT 1
            """
        )
    ).scalar_one_or_none()
    if admin_user_id is not None:
        return int(admin_user_id)

    any_user_id = connection.execute(sa.text("SELECT id FROM users ORDER BY id ASC LIMIT 1")).scalar_one_or_none()
    if any_user_id is None:
        return None
    return int(any_user_id)


def _backfill_diary_created_by(connection):
    diary_ids = [
        int(row[0])
        for row in connection.execute(
            sa.text(
                """
                SELECT id
                FROM jigsaw_diary_entries
                WHERE created_by_user_id IS NULL
                ORDER BY id ASC
                """
            )
        ).all()
    ]
    if not diary_ids:
        return

    fallback_user_id = _resolve_fallback_user_id(connection)
    if fallback_user_id is None:
        raise RuntimeError("Cannot backfill jigsaw_diary_entries.created_by_user_id without at least one user.")

    audit_rows = connection.execute(
        sa.text(
            """
            SELECT entity_id, actor_user_id
            FROM audit_events
            WHERE entity_type = 'jigsaw_diary_entry'
              AND action IN ('jigsaw.diary_entry_created', 'jigsaw.diary_entry_created_from_image')
              AND actor_user_id IS NOT NULL
            ORDER BY id ASC
            """
        )
    ).all()

    actor_by_entry_id = {}
    for entity_id, actor_user_id in audit_rows:
        if actor_user_id is None:
            continue
        try:
            parsed_entry_id = int(str(entity_id))
        except (TypeError, ValueError):
            continue
        actor_by_entry_id.setdefault(parsed_entry_id, int(actor_user_id))

    for entry_id in diary_ids:
        created_by_user_id = actor_by_entry_id.get(entry_id, fallback_user_id)
        connection.execute(
            sa.text(
                """
                UPDATE jigsaw_diary_entries
                SET created_by_user_id = :created_by_user_id
                WHERE id = :entry_id
                """
            ),
            {"created_by_user_id": int(created_by_user_id), "entry_id": int(entry_id)},
        )


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("jigsaw_images") as batch_op:
        batch_op.add_column(sa.Column("uploaded_by_user_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            op.f("fk_jigsaw_images_uploaded_by_user_id_users"),
            "users",
            ["uploaded_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            op.f("ix_jigsaw_images_uploaded_by_user_id"),
            ["uploaded_by_user_id"],
            unique=False,
        )

    with op.batch_alter_table("jigsaw_diary_entries") as batch_op:
        batch_op.add_column(sa.Column("created_by_user_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("updated_by_user_id", sa.Integer(), nullable=True))

    connection = op.get_bind()
    _backfill_diary_created_by(connection)

    with op.batch_alter_table("jigsaw_diary_entries") as batch_op:
        batch_op.alter_column("created_by_user_id", existing_type=sa.Integer(), nullable=False)
        batch_op.create_foreign_key(
            op.f("fk_jigsaw_diary_entries_created_by_user_id_users"),
            "users",
            ["created_by_user_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            op.f("fk_jigsaw_diary_entries_updated_by_user_id_users"),
            "users",
            ["updated_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            op.f("ix_jigsaw_diary_entries_created_by_user_id"),
            ["created_by_user_id"],
            unique=False,
        )
        batch_op.create_index(
            op.f("ix_jigsaw_diary_entries_updated_by_user_id"),
            ["updated_by_user_id"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("jigsaw_diary_entries") as batch_op:
        batch_op.drop_index(op.f("ix_jigsaw_diary_entries_updated_by_user_id"))
        batch_op.drop_index(op.f("ix_jigsaw_diary_entries_created_by_user_id"))
        batch_op.drop_constraint(op.f("fk_jigsaw_diary_entries_updated_by_user_id_users"), type_="foreignkey")
        batch_op.drop_constraint(op.f("fk_jigsaw_diary_entries_created_by_user_id_users"), type_="foreignkey")
        batch_op.drop_column("updated_by_user_id")
        batch_op.drop_column("created_by_user_id")

    with op.batch_alter_table("jigsaw_images") as batch_op:
        batch_op.drop_index(op.f("ix_jigsaw_images_uploaded_by_user_id"))
        batch_op.drop_constraint(op.f("fk_jigsaw_images_uploaded_by_user_id_users"), type_="foreignkey")
        batch_op.drop_column("uploaded_by_user_id")
