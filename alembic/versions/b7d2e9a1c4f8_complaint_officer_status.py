"""complaint officer assignment and status

Revision ID: b7d2e9a1c4f8
Revises: a3f1c2d4e5b6
Create Date: 2026-10-21 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b7d2e9a1c4f8'
down_revision: Union[str, Sequence[str], None] = 'a3f1c2d4e5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add officer assignment, officer status and resolution columns."""
    op.add_column('complaints', sa.Column('officer_id', sa.Integer(), nullable=True))
    op.add_column('complaints', sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('complaints', sa.Column('officer_status', sa.String(length=20), server_default='pending', nullable=False))
    op.add_column('complaints', sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('complaints', sa.Column('resolved_photo_url', sa.String(length=500), nullable=True))
    op.create_index(op.f('ix_complaints_officer_id'), 'complaints', ['officer_id'], unique=False)
    op.create_foreign_key(
        'fk_complaints_officer_id', 'complaints', 'officers',
        ['officer_id'], ['id'], ondelete='SET NULL',
    )


def downgrade() -> None:
    """Remove the officer columns. Assignment and resolution data is lost."""
    op.drop_constraint('fk_complaints_officer_id', 'complaints', type_='foreignkey')
    op.drop_index(op.f('ix_complaints_officer_id'), table_name='complaints')
    op.drop_column('complaints', 'resolved_photo_url')
    op.drop_column('complaints', 'resolved_at')
    op.drop_column('complaints', 'officer_status')
    op.drop_column('complaints', 'assigned_at')
    op.drop_column('complaints', 'officer_id')
