"""add email verification fields to user

Revision ID: 54e4a8f7c08c
Revises: c3d4e5f6a7b8
Create Date: 2026-01-30 22:35:48.128464

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '54e4a8f7c08c'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def upgrade():
    # Add email verification fields to user table
    op.add_column('user', sa.Column('email_verified', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('user', sa.Column('email_verified_at', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('user', 'email_verified_at')
    op.drop_column('user', 'email_verified')
