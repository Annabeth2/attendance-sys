"""add bluetooth_address to attendances

Revision ID: add_bluetooth_address
Revises: 
Create Date: 2024-03-19

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_bluetooth_address'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Add bluetooth_address column to attendances table
    op.add_column('attendances', sa.Column('bluetooth_address', sa.String(), nullable=True))

def downgrade():
    # Remove bluetooth_address column from attendances table
    op.drop_column('attendances', 'bluetooth_address') 