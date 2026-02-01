"""Add system_config table

Revision ID: 269f5c9fb0f6
Revises: 306ad2248fd6
Create Date: 2026-02-01 13:37:23.036482

"""

import sqlalchemy as sa
import sqlmodel.sql.sqltypes

from alembic import op

# revision identifiers, used by Alembic.
revision = "269f5c9fb0f6"
down_revision = "306ad2248fd6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "systemconfig",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "key", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False
        ),
        sa.Column(
            "value", sqlmodel.sql.sqltypes.AutoString(length=1000), nullable=False
        ),
        sa.Column(
            "description", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_systemconfig_key"), "systemconfig", ["key"], unique=True)


def downgrade():
    op.drop_index(op.f("ix_systemconfig_key"), table_name="systemconfig")
    op.drop_table("systemconfig")
