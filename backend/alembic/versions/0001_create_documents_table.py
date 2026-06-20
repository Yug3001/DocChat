"""create documents table

Revision ID: 0001
Revises:
Create Date: 2026-06-05
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'documents',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('original_filename', sa.String(255), nullable=True),
        sa.Column('file_type', sa.String(20), nullable=False),
        sa.Column('session_id', sa.String(36), nullable=False),
        sa.Column('storage_path', sa.String(512), nullable=False),
        sa.Column('chunk_count', sa.Integer(), default=0),
        sa.Column('file_size', sa.Integer(), default=0),
        sa.Column('is_excel', sa.Boolean(), default=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False
        ),
        sa.Column('status', sa.String(20), default='processing'),
    )
    op.create_index('ix_documents_session_id', 'documents', ['session_id'])


def downgrade() -> None:
    op.drop_index('ix_documents_session_id', table_name='documents')
    op.drop_table('documents')