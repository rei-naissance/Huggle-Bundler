"""
Drop seller_id from bundles and its index
"""
from alembic import op
import sqlalchemy as sa
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = '0003_drop_seller_id'
down_revision: Union[str, None] = '0002_make_seller_id_nullable'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop index if exists, then column
    op.execute("DROP INDEX IF EXISTS ix_bundles_seller_id")
    op.drop_column('bundles', 'seller_id')


def downgrade() -> None:
    # Re-add column as nullable and recreate index
    op.add_column('bundles', sa.Column('seller_id', sa.String(), nullable=True))
    op.create_index('ix_bundles_seller_id', 'bundles', ['seller_id'])