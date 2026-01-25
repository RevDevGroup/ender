"""initial_schema

Revision ID: af127e65d03b
Revises:
Create Date: 2026-01-25 10:34:58.609842

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = 'af127e65d03b'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Initial schema - database already contains all tables
    pass


def downgrade():
    # Cannot downgrade from initial schema
    pass
