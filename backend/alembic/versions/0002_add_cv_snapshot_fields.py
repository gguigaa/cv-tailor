"""add prompt_used and cv_snapshot to generated_cvs

Revision ID: 0002
Revises: 0001
Create Date: 2026-01-01 00:00:01.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('generated_cvs', sa.Column('prompt_used', sa.Text(), nullable=True))
    op.add_column('generated_cvs', sa.Column('cv_snapshot', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('generated_cvs', 'prompt_used')
    op.drop_column('generated_cvs', 'cv_snapshot')