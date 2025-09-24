"""
Make seller_id nullable in bundles table
"""
from alembic import op
import sqlalchemy as sa
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = '0002_make_seller_id_nullable'
down_revision: Union[str, None] = '0001_create_bundles_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('bundles', 'seller_id', existing_type=sa.String(), nullable=True)


def downgrade() -> None:
    op.alter_column('bundles', 'seller_id', existing_type=sa.String(), nullable=False)