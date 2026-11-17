"""complaint notification wamid

Revision ID: c4e8f1a7b2d9
Revises: b7d2e9a1c4f8
Create Date: 2026-10-23 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c4e8f1a7b2d9'
down_revision: Union[str, Sequence[str], None] = 'b7d2e9a1c4f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the id of the officer's alert message."""
    op.add_column('complaints', sa.Column('notification_wamid', sa.String(length=128), nullable=True))
    op.create_index(op.f('ix_complaints_notification_wamid'), 'complaints', ['notification_wamid'], unique=False)


def downgrade() -> None:
    """Remove the alert message id."""
    op.drop_index(op.f('ix_complaints_notification_wamid'), table_name='complaints')
    op.drop_column('complaints', 'notification_wamid')
