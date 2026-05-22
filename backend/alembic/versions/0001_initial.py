"""initial schema

Revision ID: 0001
Revises: 
Create Date: 2026-01-01 00:00:00.000000
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
        'users',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('username', sa.String(), nullable=False, unique=True, index=True),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_admin', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        'cv_profiles',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), unique=True, nullable=False),
        sa.Column('cv_pt', sa.Text(), nullable=True),
        sa.Column('cv_en', sa.Text(), nullable=True),
        sa.Column('base_prompt', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        'generated_cvs',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('job_description', sa.Text(), nullable=False),
        sa.Column('result', sa.Text(), nullable=False),
        sa.Column('lang', sa.String(2), default='pt'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('generated_cvs')
    op.drop_table('cv_profiles')
    op.drop_table('users')