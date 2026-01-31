"""Add subscription and payment tables

Revision ID: 3c714296816f
Revises: 7072efaa93c4
Create Date: 2026-01-31 18:24:10.669598

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = '3c714296816f'
down_revision = '7072efaa93c4'
branch_labels = None
depends_on = None


def upgrade():
    # Create subscription table
    op.create_table('subscription',
    sa.Column('billing_cycle', sa.Enum('MONTHLY', 'YEARLY', name='billingcycle'), nullable=False),
    sa.Column('status', sa.Enum('PENDING', 'ACTIVE', 'PAST_DUE', 'CANCELED', 'EXPIRED', name='subscriptionstatus'), nullable=False),
    sa.Column('cancel_at_period_end', sa.Boolean(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('plan_id', sa.Uuid(), nullable=False),
    sa.Column('current_period_start', sa.DateTime(), nullable=False),
    sa.Column('current_period_end', sa.DateTime(), nullable=False),
    sa.Column('canceled_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['plan_id'], ['userplan.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id')
    )

    # Create payment table
    op.create_table('payment',
    sa.Column('amount', sa.Float(), nullable=False),
    sa.Column('currency', sqlmodel.sql.sqltypes.AutoString(length=10), nullable=False),
    sa.Column('status', sa.Enum('PENDING', 'COMPLETED', 'FAILED', 'REFUNDED', name='paymentstatus'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('subscription_id', sa.Uuid(), nullable=False),
    sa.Column('provider', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
    sa.Column('provider_transaction_id', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
    sa.Column('provider_invoice_id', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
    sa.Column('provider_invoice_url', sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
    sa.Column('period_start', sa.DateTime(), nullable=False),
    sa.Column('period_end', sa.DateTime(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('paid_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['subscription_id'], ['subscription.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payment_provider_invoice_id'), 'payment', ['provider_invoice_id'], unique=False)
    op.create_index(op.f('ix_payment_provider_transaction_id'), 'payment', ['provider_transaction_id'], unique=True)

    # Add new columns to userplan
    op.add_column('userplan', sa.Column('price_yearly', sa.Float(), nullable=False, server_default='0'))
    op.add_column('userplan', sa.Column('is_public', sa.Boolean(), nullable=False, server_default='true'))


def downgrade():
    # Remove columns from userplan
    op.drop_column('userplan', 'is_public')
    op.drop_column('userplan', 'price_yearly')

    # Drop payment table
    op.drop_index(op.f('ix_payment_provider_transaction_id'), table_name='payment')
    op.drop_index(op.f('ix_payment_provider_invoice_id'), table_name='payment')
    op.drop_table('payment')

    # Drop subscription table
    op.drop_table('subscription')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS paymentstatus')
    op.execute('DROP TYPE IF EXISTS subscriptionstatus')
    op.execute('DROP TYPE IF EXISTS billingcycle')
