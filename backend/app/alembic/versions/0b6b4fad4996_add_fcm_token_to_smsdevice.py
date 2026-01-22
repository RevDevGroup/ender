"""add_fcm_token_to_smsdevice

Revision ID: 0b6b4fad4996
Revises: db80539b8422
Create Date: 2026-01-21

"""

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = "0b6b4fad4996"
down_revision = "db80539b8422"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "smsdevice",
        sa.Column(
            "fcm_token", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True
        ),
    )


def downgrade():
    op.drop_column("smsdevice", "fcm_token")
