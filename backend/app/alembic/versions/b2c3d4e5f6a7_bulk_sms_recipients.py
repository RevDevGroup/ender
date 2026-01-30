"""bulk_sms_batch_id

Revision ID: b2c3d4e5f6a7
Revises: af127e65d03b
Create Date: 2026-01-26

Changes:
- Rename recipients -> to in smsmessage
- Add batch_id to smsmessage for grouping bulk sends
- Drop smsrecipientstatus table (no longer needed)
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = 'af127e65d03b'
branch_labels = None
depends_on = None


def upgrade():
    # Add batch_id column to smsmessage
    op.add_column('smsmessage', sa.Column('batch_id', sa.Uuid(), nullable=True))
    op.create_index(op.f('ix_smsmessage_batch_id'), 'smsmessage', ['batch_id'], unique=False)

    # Rename recipients to "to" if recipients exists
    # First check and handle the column rename
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='smsmessage' AND column_name='recipients') THEN
                ALTER TABLE smsmessage RENAME COLUMN recipients TO "to";
                ALTER TABLE smsmessage ALTER COLUMN "to" TYPE VARCHAR(20);
            END IF;
        END $$;
    """)

    # Drop smsrecipientstatus table if it exists
    op.execute("DROP TABLE IF EXISTS smsrecipientstatus CASCADE")


def downgrade():
    # Drop batch_id column
    op.drop_index(op.f('ix_smsmessage_batch_id'), table_name='smsmessage')
    op.drop_column('smsmessage', 'batch_id')

    # Rename "to" back to recipients
    op.execute('ALTER TABLE smsmessage RENAME COLUMN "to" TO recipients')
    op.execute('ALTER TABLE smsmessage ALTER COLUMN recipients TYPE VARCHAR(5000)')
