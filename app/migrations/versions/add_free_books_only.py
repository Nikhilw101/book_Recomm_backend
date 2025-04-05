"""add free_books_only field

Revision ID: add_free_books_only
Revises: previous_revision_id
Create Date: 2024-03-14 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_free_books_only'
down_revision = 'previous_revision_id'  # Replace with your previous migration ID
branch_labels = None
depends_on = None

def upgrade():
    # Add free_books_only column to book_preferences table
    op.add_column('book_preferences', sa.Column('free_books_only', sa.Boolean(), nullable=False, server_default='false'))
    
    # Add created_at and updated_at columns
    op.add_column('book_preferences', sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')))
    op.add_column('book_preferences', sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')))

def downgrade():
    # Remove the columns
    op.drop_column('book_preferences', 'free_books_only')
    op.drop_column('book_preferences', 'created_at')
    op.drop_column('book_preferences', 'updated_at') 