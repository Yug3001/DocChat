"""fix documents created_at default

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-09
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if created_at column exists, if not add it
    # Also ensure it has a default value
    op.alter_column('documents', 'created_at',
                   existing_type=sa.DateTime(timezone=True),
                   server_default=sa.text('CURRENT_TIMESTAMP'),
                   existing_nullable=True,
                   nullable=False)


def downgrade() -> None:
    op.alter_column('documents', 'created_at',
                   existing_type=sa.DateTime(timezone=True),
                   server_default=None,
                   existing_nullable=False,
                   nullable=True)
