"""create initial schema

Revision ID: c67b672955db
Revises: 
Create Date: 2026-06-22 11:30:22.308933

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c67b672955db'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_roles')),
        sa.UniqueConstraint('name', name=op.f('uq_roles_name')),
    )

    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=True),
        sa.Column('auth_subject', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
        sa.UniqueConstraint('email', name=op.f('uq_users_email')),
    )

    op.create_table(
        'jigsaws',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('piece_count', sa.Integer(), nullable=False),
        sa.Column('condition', sa.String(length=64), nullable=True),
        sa.Column(
            'status',
            sa.Enum('available', 'on_loan', 'maintenance', 'retired', name='jigsaw_status', native_enum=False),
            nullable=False,
        ),
        sa.Column('tags', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('piece_count > 0', name='ck_jigsaws_piece_count_positive'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_jigsaws')),
    )
    op.create_index(op.f('ix_jigsaws_status'), 'jigsaws', ['status'], unique=False)

    op.create_table(
        'user_roles',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], name=op.f('fk_user_roles_role_id_roles'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_user_roles_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'role_id', name=op.f('pk_user_roles')),
    )

    op.create_table(
        'loans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('borrower_user_id', sa.Integer(), nullable=False),
        sa.Column('jigsaw_id', sa.Integer(), nullable=False),
        sa.Column('checked_out_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('due_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('returned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'status',
            sa.Enum('active', 'returned', 'overdue', name='loan_status', native_enum=False),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['borrower_user_id'], ['users.id'], name=op.f('fk_loans_borrower_user_id_users')),
        sa.ForeignKeyConstraint(['jigsaw_id'], ['jigsaws.id'], name=op.f('fk_loans_jigsaw_id_jigsaws')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_loans')),
    )
    op.create_index(op.f('ix_loans_borrower_user_id'), 'loans', ['borrower_user_id'], unique=False)
    op.create_index(op.f('ix_loans_jigsaw_id'), 'loans', ['jigsaw_id'], unique=False)
    op.create_index(op.f('ix_loans_status'), 'loans', ['status'], unique=False)

    op.create_table(
        'audit_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('actor_user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=128), nullable=False),
        sa.Column('entity_type', sa.String(length=64), nullable=False),
        sa.Column('entity_id', sa.String(length=64), nullable=False),
        sa.Column('request_id', sa.String(length=64), nullable=True),
        sa.Column('remote_addr', sa.String(length=64), nullable=True),
        sa.Column('client_ip_resolved', sa.String(length=64), nullable=True),
        sa.Column('forwarded_chain', sa.Text(), nullable=True),
        sa.Column('scheme', sa.String(length=16), nullable=True),
        sa.Column('host', sa.String(length=255), nullable=True),
        sa.Column('payload_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'], name=op.f('fk_audit_events_actor_user_id_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_events')),
    )
    op.create_index(op.f('ix_audit_events_action'), 'audit_events', ['action'], unique=False)
    op.create_index(op.f('ix_audit_events_entity_type'), 'audit_events', ['entity_type'], unique=False)
    op.create_index(op.f('ix_audit_events_request_id'), 'audit_events', ['request_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_audit_events_request_id'), table_name='audit_events')
    op.drop_index(op.f('ix_audit_events_entity_type'), table_name='audit_events')
    op.drop_index(op.f('ix_audit_events_action'), table_name='audit_events')
    op.drop_table('audit_events')

    op.drop_index(op.f('ix_loans_status'), table_name='loans')
    op.drop_index(op.f('ix_loans_jigsaw_id'), table_name='loans')
    op.drop_index(op.f('ix_loans_borrower_user_id'), table_name='loans')
    op.drop_table('loans')

    op.drop_table('user_roles')

    op.drop_index(op.f('ix_jigsaws_status'), table_name='jigsaws')
    op.drop_table('jigsaws')

    op.drop_table('users')
    op.drop_table('roles')
