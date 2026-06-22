"""allow empty jigsaw create fields

Revision ID: 2d3a9be41f7c
Revises: 9a7d2f4c1b88
Create Date: 2026-06-22 23:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2d3a9be41f7c"
down_revision: Union[str, Sequence[str], None] = "9a7d2f4c1b88"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    check_constraints = {constraint.get("name") for constraint in inspector.get_check_constraints("jigsaws")}

    with op.batch_alter_table("jigsaws") as batch_op:
        if "ck_jigsaws_piece_count_positive" in check_constraints:
            batch_op.drop_constraint("ck_jigsaws_piece_count_positive", type_="check")

        batch_op.alter_column("title", existing_type=sa.String(length=255), nullable=True)
        batch_op.alter_column("piece_count", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(sa.text("UPDATE jigsaws SET title = '' WHERE title IS NULL"))
    op.execute(sa.text("UPDATE jigsaws SET piece_count = 1 WHERE piece_count IS NULL OR piece_count <= 0"))

    with op.batch_alter_table("jigsaws") as batch_op:
        batch_op.alter_column("title", existing_type=sa.String(length=255), nullable=False)
        batch_op.alter_column("piece_count", existing_type=sa.Integer(), nullable=False)
        batch_op.create_check_constraint("ck_jigsaws_piece_count_positive", "piece_count > 0")
