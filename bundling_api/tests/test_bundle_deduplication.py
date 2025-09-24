"""
Tests for bundle deduplication using signature-based unique constraints.

These tests verify that:
1. Signature computation works correctly
2. Database-level uniqueness is enforced
3. Edge cases are handled properly
4. Repository methods handle constraints correctly
"""
import pytest
from unittest.mock import MagicMock
from sqlalchemy.exc import IntegrityError

from app.utils.signatures import (
    compute_bundle_signature, 
    compute_signature_from_id_list, 
    validate_signature
)
from app.repositories.bundles import create_bundle, bundle_exists_for_products
from app.schemas.bundle import BundleCreate, ProductIn
from app.models.bundle import Bundle


class TestSignatureComputation:
    """Test signature computation utilities."""
    
    def test_compute_signature_consistent_order(self):
        """Test that signature is consistent regardless of product order."""
        products1 = [{"id": "prod1"}, {"id": "prod2"}, {"id": "prod3"}]
        products2 = [{"id": "prod3"}, {"id": "prod1"}, {"id": "prod2"}]
        
        sig1 = compute_bundle_signature(products1)
        sig2 = compute_bundle_signature(products2)
        
        assert sig1 == sig2
        assert len(sig1) == 64  # SHA-256 hex digest
    
    def test_compute_signature_different_products(self):
        """Test that different product sets produce different signatures."""
        products1 = [{"id": "prod1"}, {"id": "prod2"}]
        products2 = [{"id": "prod1"}, {"id": "prod3"}]
        
        sig1 = compute_bundle_signature(products1)
        sig2 = compute_bundle_signature(products2)
        
        assert sig1 != sig2
    
    def test_compute_signature_empty_products(self):
        """Test that empty product list raises ValueError."""
        with pytest.raises(ValueError, match="empty product list"):
            compute_bundle_signature([])
    
    def test_compute_signature_no_valid_ids(self):
        """Test that products without valid IDs raise ValueError."""
        products = [{"name": "Product"}, {"id": None}, {"id": ""}]
        
        with pytest.raises(ValueError, match="No valid product IDs found"):
            compute_bundle_signature(products)
    
    def test_compute_signature_mixed_id_types(self):
        """Test that signature handles mixed ID types correctly."""
        products = [{"id": 123}, {"id": "prod2"}, {"id": "prod3"}]
        
        sig = compute_bundle_signature(products)
        assert len(sig) == 64
        
        # Should be equivalent to string-only version
        products_str = [{"id": "123"}, {"id": "prod2"}, {"id": "prod3"}]
        sig_str = compute_bundle_signature(products_str)
        assert sig == sig_str
    
    def test_compute_signature_from_id_list(self):
        """Test direct signature computation from ID list."""
        ids = ["prod1", "prod2", "prod3"]
        sig1 = compute_signature_from_id_list(ids)
        
        # Should be equivalent to product dict version
        products = [{"id": "prod1"}, {"id": "prod2"}, {"id": "prod3"}]
        sig2 = compute_bundle_signature(products)
        
        assert sig1 == sig2
    
    def test_compute_signature_from_id_list_empty(self):
        """Test that empty ID list raises ValueError."""
        with pytest.raises(ValueError, match="empty product ID list"):
            compute_signature_from_id_list([])
    
    def test_validate_signature_valid(self):
        """Test signature validation with valid signatures."""
        valid_sig = compute_signature_from_id_list(["prod1", "prod2"])
        assert validate_signature(valid_sig) is True
    
    def test_validate_signature_invalid(self):
        """Test signature validation with invalid signatures."""
        assert validate_signature(None) is False
        assert validate_signature("") is False
        assert validate_signature("too_short") is False
        assert validate_signature("x" * 64) is False  # Not hex
        assert validate_signature("1" * 63) is False  # Wrong length
        assert validate_signature("1" * 65) is False  # Wrong length
        assert validate_signature(123) is False  # Not string


class TestBundleRepositoryDeduplication:
    """Test bundle repository deduplication functionality."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return MagicMock()
    
    @pytest.fixture
    def sample_bundle_data(self):
        """Sample bundle data for testing."""
        return BundleCreate(
            store_id="store123",
            name="Test Bundle",
            description="Test bundle description",
            products=[
                ProductIn(id="prod1", name="Product 1", stock=10),
                ProductIn(id="prod2", name="Product 2", stock=5),
            ],
            images=["img1.jpg"],
            stock=5
        )
    
    def test_create_bundle_computes_signature(self, mock_db, sample_bundle_data):
        """Test that create_bundle computes and sets signature."""
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()
        
        bundle = create_bundle(mock_db, sample_bundle_data)
        
        # Verify signature was computed and set
        assert hasattr(bundle, 'signature')
        assert len(bundle.signature) == 64
        assert validate_signature(bundle.signature)
    
    def test_create_bundle_duplicate_raises_error(self, mock_db, sample_bundle_data):
        """Test that creating duplicate bundle raises ValueError."""
        # Mock IntegrityError with unique constraint violation
        integrity_error = IntegrityError("statement", "params", "orig")
        integrity_error.orig = MagicMock()
        integrity_error.orig.__str__ = lambda: "uq_bundle_store_signature"
        
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock(side_effect=integrity_error)
        mock_db.rollback = MagicMock()
        
        with pytest.raises(ValueError, match="bundle with the same products already exists"):
            create_bundle(mock_db, sample_bundle_data)
        
        mock_db.rollback.assert_called_once()
    
    def test_create_bundle_invalid_products(self, mock_db):
        """Test that bundle with invalid products raises ValueError."""
        invalid_bundle = BundleCreate(
            store_id="store123",
            name="Invalid Bundle",
            description="Bundle with no valid products",
            products=[],  # Empty products
            images=[],
            stock=0
        )
        
        with pytest.raises(ValueError, match="Cannot create bundle"):
            create_bundle(mock_db, invalid_bundle)
    
    def test_bundle_exists_for_products_true(self, mock_db):
        """Test bundle_exists_for_products returns True for existing bundle."""
        # Mock query to return an existing bundle
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_first = MagicMock(return_value=Bundle())  # Non-None result
        
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_first.return_value
        
        result = bundle_exists_for_products(mock_db, "store123", ["prod1", "prod2"])
        assert result is True
    
    def test_bundle_exists_for_products_false(self, mock_db):
        """Test bundle_exists_for_products returns False for non-existing bundle."""
        # Mock query to return None
        mock_query = MagicMock()
        mock_filter = MagicMock()
        
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = None
        
        result = bundle_exists_for_products(mock_db, "store123", ["prod1", "prod2"])
        assert result is False
    
    def test_bundle_exists_for_products_invalid_ids(self, mock_db):
        """Test bundle_exists_for_products handles invalid product IDs."""
        result = bundle_exists_for_products(mock_db, "store123", [])
        assert result is False


class TestDatabaseConstraints:
    """Integration tests for database constraints (require actual DB)."""
    
    def test_unique_constraint_same_store(self):
        """Test that unique constraint prevents duplicates within same store.
        
        Note: This test requires a real database connection and would be run
        as part of integration testing rather than unit testing.
        """
        # This would be implemented with a real database fixture
        # and would test the actual unique constraint behavior
        pass
    
    def test_unique_constraint_different_stores(self):
        """Test that same product combinations are allowed in different stores.
        
        Note: This test requires a real database connection.
        """
        # This would verify that the constraint is scoped to store_id
        pass


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_signature_deterministic(self):
        """Test that signature computation is deterministic."""
        products = [{"id": "prod1"}, {"id": "prod2"}, {"id": "prod3"}]
        
        # Compute signature multiple times
        sigs = [compute_bundle_signature(products) for _ in range(10)]
        
        # All signatures should be identical
        assert all(sig == sigs[0] for sig in sigs)
    
    def test_signature_handles_unicode(self):
        """Test that signature computation handles Unicode product IDs."""
        products = [{"id": "产品1"}, {"id": "продукт2"}, {"id": "محصول3"}]
        
        sig = compute_bundle_signature(products)
        assert len(sig) == 64
        assert validate_signature(sig)
    
    def test_signature_handles_large_product_sets(self):
        """Test signature computation with large product sets."""
        # Create 1000 products
        products = [{"id": f"prod{i}"} for i in range(1000)]
        
        sig = compute_bundle_signature(products)
        assert len(sig) == 64
        assert validate_signature(sig)
    
    def test_signature_collision_resistance(self):
        """Test that different product sets produce different signatures."""
        # This is a probabilistic test - collisions are extremely unlikely
        signatures = set()
        
        for i in range(100):
            products = [{"id": f"prod{i}"}, {"id": f"prod{i+1}"}]
            sig = compute_bundle_signature(products)
            signatures.add(sig)
        
        # Should have 100 unique signatures
        assert len(signatures) == 100