"""officers

Revision ID: a3f1c2d4e5b6
Revises: ddbcb8b1fc96
Create Date: 2026-10-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a3f1c2d4e5b6'
down_revision: Union[str, Sequence[str], None] = 'ddbcb8b1fc96'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the officers table, one officer per local body."""
    op.create_table('officers',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('phone', sa.String(length=20), nullable=False),
    sa.Column('local_body', sa.String(length=80), nullable=False),
    sa.Column('escalation_officer_id', sa.Integer(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['escalation_officer_id'], ['officers.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('local_body')
    )


def downgrade() -> None:
    """Drop the officers table. All officer rows are lost."""
    op.drop_table('officers')
