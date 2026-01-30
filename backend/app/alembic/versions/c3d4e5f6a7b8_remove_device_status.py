"""remove_device_status

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-01-30

Changes:
- Remove status column from smsdevice table
- Remove last_heartbeat column from smsdevice table
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade():
    # Remove status column from smsdevice
    op.drop_column('smsdevice', 'status')

    # Remove last_heartbeat column from smsdevice
    op.drop_column('smsdevice', 'last_heartbeat')


def downgrade():
    # Add back status column
    op.add_column('smsdevice', sa.Column('status', sa.VARCHAR(length=50), nullable=True))
    op.execute("UPDATE smsdevice SET status = 'offline' WHERE status IS NULL")
    op.alter_column('smsdevice', 'status', nullable=False, server_default='offline')

    # Add back last_heartbeat column
    op.add_column('smsdevice', sa.Column('last_heartbeat', sa.TIMESTAMP(timezone=True), nullable=True))
