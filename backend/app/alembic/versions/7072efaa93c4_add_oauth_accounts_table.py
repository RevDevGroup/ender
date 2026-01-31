"""Add OAuth accounts table

Revision ID: 7072efaa93c4
Revises: 54e4a8f7c08c
Create Date: 2026-01-31 10:52:50.307122

"""

import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op

# revision identifiers, used by Alembic.
revision = "7072efaa93c4"
down_revision = "54e4a8f7c08c"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "oauthaccount",
        sa.Column(
            "provider",
            sqlmodel.sql.sqltypes.AutoString(length=50),
            nullable=False,
        ),
        sa.Column(
            "provider_user_id",
            sqlmodel.sql.sqltypes.AutoString(length=255),
            nullable=False,
        ),
        sa.Column(
            "provider_email",
            sqlmodel.sql.sqltypes.AutoString(length=255),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "access_token",
            sqlmodel.sql.sqltypes.AutoString(length=2000),
            nullable=True,
        ),
        sa.Column(
            "refresh_token",
            sqlmodel.sql.sqltypes.AutoString(length=2000),
            nullable=True,
        ),
        sa.Column("token_expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_oauthaccount_provider"), "oauthaccount", ["provider"], unique=False
    )
    # Unique constraint: one OAuth account per provider per user
    op.create_unique_constraint(
        "uq_oauthaccount_user_provider", "oauthaccount", ["user_id", "provider"]
    )
    # Unique constraint: provider_user_id must be unique per provider
    op.create_unique_constraint(
        "uq_oauthaccount_provider_user_id",
        "oauthaccount",
        ["provider", "provider_user_id"],
    )
    # Make hashed_password nullable for OAuth-only users
    op.alter_column(
        "user", "hashed_password", existing_type=sa.VARCHAR(), nullable=True
    )


def downgrade():
    op.alter_column(
        "user", "hashed_password", existing_type=sa.VARCHAR(), nullable=False
    )
    op.drop_constraint("uq_oauthaccount_provider_user_id", "oauthaccount")
    op.drop_constraint("uq_oauthaccount_user_provider", "oauthaccount")
    op.drop_index(op.f("ix_oauthaccount_provider"), table_name="oauthaccount")
    op.drop_table("oauthaccount")
