"""merge heads

Revision ID: merge_heads
Revises: 74a48ee8cc04, add_chat_features
Create Date: 2024-01-30 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'merge_heads'
down_revision = ('74a48ee8cc04', 'add_chat_features')
branch_labels = None
depends_on = None

def upgrade():
    pass

def downgrade():
    pass
