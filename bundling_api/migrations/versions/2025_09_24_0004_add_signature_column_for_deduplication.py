"""
Add signature column for bundle deduplication

Revision ID: 0004_add_signature_column
Revises: 0003_drop_seller_id
Create Date: 2025-09-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = '0004_add_signature_column'
down_revision: Union[str, None] = '0003_drop_seller_id'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add signature column and unique constraint for deduplication."""
    
    # Add the signature column - NOT NULL but will be populated in next step
    op.add_column('bundles', sa.Column('signature', sa.String(64), nullable=True))
    
    # Populate signatures for existing bundles
    # This SQL function computes the signature from existing product data
    # Handle edge cases: empty arrays, null products, missing IDs
    populate_signatures_sql = """
    UPDATE bundles 
    SET signature = (
        CASE 
            WHEN products IS NULL OR jsonb_array_length(products) = 0 THEN 
                -- For empty/null products, use a special signature based on bundle ID
                encode(sha256(('empty_bundle_' || id::text)::bytea), 'hex')
            ELSE
                -- Compute signature from product IDs
                encode(
                    sha256(
                        COALESCE(
                            (
                                SELECT string_agg(id_val, '|' ORDER BY id_val)
                                FROM (
                                    SELECT DISTINCT elem->>'id' AS id_val
                                    FROM jsonb_array_elements(bundles.products) AS elem
                                    WHERE elem->>'id' IS NOT NULL 
                                      AND elem->>'id' != ''
                                      AND elem->>'id' != 'null'
                                ) AS sorted_ids
                                WHERE id_val IS NOT NULL
                            ),
                            'no_valid_products_' || bundles.id::text
                        )::bytea
                    ), 
                    'hex'
                )
        END
    )
    WHERE signature IS NULL;
    """
    
    op.execute(text(populate_signatures_sql))
    
    # Remove duplicate bundles before creating unique constraint
    # Keep the oldest bundle (lowest ID) for each (store_id, signature) combination
    
    # First, count how many duplicates we have
    count_duplicates_sql = """
    SELECT COUNT(*) - COUNT(DISTINCT (store_id, signature)) AS duplicate_count
    FROM bundles WHERE signature IS NOT NULL;
    """
    
    print("\n⚠️  Checking for duplicate bundles...")
    
    remove_duplicates_sql = """
    DELETE FROM bundles 
    WHERE id NOT IN (
        SELECT MIN(id)
        FROM bundles 
        WHERE signature IS NOT NULL
        GROUP BY store_id, signature
    );
    """
    
    result = op.execute(text(remove_duplicates_sql))
    removed_count = result.rowcount if result and hasattr(result, 'rowcount') and result.rowcount else 0
    print(f"✅ Removed {removed_count} duplicate bundles")
    print("   (Kept the oldest bundle for each unique product combination)")
    
    # Now make the column NOT NULL since all existing records have signatures
    op.alter_column('bundles', 'signature', nullable=False)
    
    # Create index on signature column for performance
    op.create_index('ix_bundles_signature', 'bundles', ['signature'])
    
    # Create unique constraint on (store_id, signature) for database-level deduplication
    op.create_unique_constraint(
        'uq_bundle_store_signature', 
        'bundles', 
        ['store_id', 'signature']
    )


def downgrade() -> None:
    """Remove signature column and related constraints."""
    
    # Drop the unique constraint first
    op.drop_constraint('uq_bundle_store_signature', 'bundles', type_='unique')
    
    # Drop the index
    op.drop_index('ix_bundles_signature', table_name='bundles')
    
    # Drop the signature column
    op.drop_column('bundles', 'signature')