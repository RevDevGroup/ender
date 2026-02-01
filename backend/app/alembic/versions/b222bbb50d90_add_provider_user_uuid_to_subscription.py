"""Add provider_user_uuid to subscription

Revision ID: b222bbb50d90
Revises: 3c714296816f
Create Date: 2026-01-31 20:21:58.663965

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = 'b222bbb50d90'
down_revision = '3c714296816f'
branch_labels = None
depends_on = None


def upgrade():
    # Add provider_user_uuid column for storing authorized payment user UUID
    op.add_column(
        'subscription',
        sa.Column(
            'provider_user_uuid',
            sqlmodel.sql.sqltypes.AutoString(length=255),
            nullable=True
        )
    )


def downgrade():
    op.drop_column('subscription', 'provider_user_uuid')
