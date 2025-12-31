"""add_sms_models

Revision ID: 38a2c006503e
Revises: 1a31ce608336
Create Date: 2025-12-30 22:06:38.233434

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '38a2c006503e'
down_revision = '1a31ce608336'
branch_labels = None
depends_on = None


def upgrade():
    # Ensure uuid-ossp extension is available
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # Create userplan table
    op.create_table(
        'userplan',
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('max_sms_per_month', sa.Integer(), nullable=False),
        sa.Column('max_devices', sa.Integer(), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_userplan_name'), 'userplan', ['name'], unique=True)

    # Create userquota table
    op.create_table(
        'userquota',
        sa.Column('sms_sent_this_month', sa.Integer(), nullable=False),
        sa.Column('devices_registered', sa.Integer(), nullable=False),
        sa.Column('last_reset_date', sa.DateTime(), nullable=False),
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['plan_id'], ['userplan.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )

    # Create smsdevice table
    op.create_table(
        'smsdevice',
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('phone_number', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('api_key', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('last_heartbeat', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_smsdevice_api_key'), 'smsdevice', ['api_key'], unique=True)

    # Create smsmessage table
    op.create_table(
        'smsmessage',
        sa.Column('to', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('from_number', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('body', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('message_type', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('webhook_sent', sa.Boolean(), nullable=False),
        sa.Column('error_message', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['device_id'], ['smsdevice.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_smsmessage_device_id'), 'smsmessage', ['device_id'], unique=False)
    op.create_index(op.f('ix_smsmessage_user_id'), 'smsmessage', ['user_id'], unique=False)
    op.create_index(op.f('ix_smsmessage_status'), 'smsmessage', ['status'], unique=False)
    op.create_index(op.f('ix_smsmessage_message_type'), 'smsmessage', ['message_type'], unique=False)

    # Create webhookconfig table
    op.create_table(
        'webhookconfig',
        sa.Column('url', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('secret_key', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('events', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_webhookconfig_user_id'), 'webhookconfig', ['user_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_webhookconfig_user_id'), table_name='webhookconfig')
    op.drop_table('webhookconfig')
    op.drop_index(op.f('ix_smsmessage_message_type'), table_name='smsmessage')
    op.drop_index(op.f('ix_smsmessage_status'), table_name='smsmessage')
    op.drop_index(op.f('ix_smsmessage_user_id'), table_name='smsmessage')
    op.drop_index(op.f('ix_smsmessage_device_id'), table_name='smsmessage')
    op.drop_table('smsmessage')
    op.drop_index(op.f('ix_smsdevice_api_key'), table_name='smsdevice')
    op.drop_table('smsdevice')
    op.drop_table('userquota')
    op.drop_index(op.f('ix_userplan_name'), table_name='userplan')
    op.drop_table('userplan')
