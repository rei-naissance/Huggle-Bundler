"""Add image_url column to bundles table

Revision ID: 0005_add_image_url_column
Revises: 0004_add_signature_column
Create Date: 2025-09-24

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0005_add_image_url_column'
down_revision = '0004_add_signature_column'
branch_labels = None
depends_on = None


def upgrade():
    # Add image_url column to bundles table
    op.add_column('bundles', sa.Column('image_url', sa.Text(), nullable=True))


def downgrade():
    # Remove image_url column from bundles table
    op.drop_column('bundles', 'image_url')