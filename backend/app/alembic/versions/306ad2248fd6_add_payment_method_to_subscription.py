"""add payment_method to subscription

Revision ID: 306ad2248fd6
Revises: b222bbb50d90
Create Date: 2026-02-01 12:09:36.819547

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '306ad2248fd6'
down_revision = 'b222bbb50d90'
branch_labels = None
depends_on = None


def upgrade():
    # Create the enum type first
    payment_method_enum = sa.Enum('INVOICE', 'AUTHORIZED', name='paymentmethod')
    payment_method_enum.create(op.get_bind(), checkfirst=True)

    # Add column with default value for existing rows
    op.add_column(
        'subscription',
        sa.Column(
            'payment_method',
            payment_method_enum,
            nullable=False,
            server_default='INVOICE'
        )
    )

    # Remove server default after adding column
    op.alter_column('subscription', 'payment_method', server_default=None)


def downgrade():
    op.drop_column('subscription', 'payment_method')

    # Drop the enum type
    payment_method_enum = sa.Enum('INVOICE', 'AUTHORIZED', name='paymentmethod')
    payment_method_enum.drop(op.get_bind(), checkfirst=True)
