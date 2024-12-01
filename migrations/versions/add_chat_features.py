"""add chat features

Revision ID: add_chat_features
Revises: 
Create Date: 2024-01-30 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = 'add_chat_features'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    tables = inspector.get_table_names()
    
    # Add last_seen and is_online columns to user table if they don't exist
    if 'user' in tables:
        columns = [col['name'] for col in inspector.get_columns('user')]
        if 'last_seen' not in columns:
            op.add_column('user', sa.Column('last_seen', sa.DateTime(), nullable=True))
        if 'is_online' not in columns:
            op.add_column('user', sa.Column('is_online', sa.Boolean(), nullable=True, default=False))
    
    # Create chat_message table if it doesn't exist
    if 'chat_message' not in tables:
        op.create_table('chat_message',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('timestamp', sa.DateTime(), nullable=True, server_default=sa.func.now()),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
            sa.PrimaryKeyConstraint('id')
        )

def downgrade():
    # Remove chat_message table
    op.drop_table('chat_message')
    
    # Remove last_seen and is_online columns from user table
    op.drop_column('user', 'is_online')
    op.drop_column('user', 'last_seen')
