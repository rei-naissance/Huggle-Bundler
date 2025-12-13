"""Add bundle pricing fields

Revision ID: 0006_add_bundle_pricing_fields
Revises: 2025_09_24_0005_add_image_url_column
Create Date: 2025-10-13 12:37:00.000000

"""
from alembic import op
import sqlalchemy as sa
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = '0006_add_bundle_pricing_fields'
down_revision: Union[str, None] = '2025_09_24_0005_add_image_url_column'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add pricing columns to bundles table
    op.add_column('bundles', sa.Column('total_price', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.00'))
    op.add_column('bundles', sa.Column('discounted_price', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('bundles', sa.Column('discount_percentage', sa.Numeric(precision=5, scale=2), nullable=True))
    op.add_column('bundles', sa.Column('savings_amount', sa.Numeric(precision=10, scale=2), nullable=True))


def downgrade() -> None:
    # Remove pricing columns from bundles table
    op.drop_column('bundles', 'savings_amount')
    op.drop_column('bundles', 'discount_percentage')
    op.drop_column('bundles', 'discounted_price')
    op.drop_column('bundles', 'total_price')