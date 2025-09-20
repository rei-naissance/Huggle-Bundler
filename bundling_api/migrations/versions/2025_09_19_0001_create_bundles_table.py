"""
Generic single-database configuration.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = '0001_create_bundles_table'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'bundles',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('seller_id', sa.String(), nullable=False),
        sa.Column('store_id', sa.String(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('products', psql.JSONB(), nullable=False),
        sa.Column('images', psql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('stock', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
    )
    # Add indices for seller_id, store_id
    op.create_index('ix_bundles_seller_id', 'bundles', ['seller_id'])
    op.create_index('ix_bundles_store_id', 'bundles', ['store_id'])


def downgrade() -> None:
    op.drop_index('ix_bundles_store_id', table_name='bundles')
    op.drop_index('ix_bundles_seller_id', table_name='bundles')
    op.drop_table('bundles')
