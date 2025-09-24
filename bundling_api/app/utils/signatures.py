"""
Utilities for computing bundle signatures for deduplication.

A signature is a deterministic hash computed from a canonicalized set of product IDs.
This enables database-level uniqueness enforcement using unique indexes.
"""
import hashlib
from typing import List, Dict, Any, Optional


def compute_bundle_signature(products: List[Dict[str, Any]]) -> str:
    """
    Compute a deterministic signature from a list of product dictionaries.
    
    The signature is computed by:
    1. Extracting product IDs from the product list
    2. Sorting them canonically (handles order independence)
    3. Creating a SHA-256 hash of the sorted, joined product IDs
    
    Args:
        products: List of product dictionaries, each containing at least an 'id' field
        
    Returns:
        A hex-encoded SHA-256 hash string representing the unique product set
        
    Raises:
        ValueError: If no valid product IDs are found
    """
    if not products:
        raise ValueError("Cannot compute signature for empty product list")
    
    # Extract and validate product IDs
    product_ids = []
    for product in products:
        if not isinstance(product, dict):
            continue
        product_id = product.get('id')
        if product_id is not None:
            product_ids.append(str(product_id))
    
    if not product_ids:
        raise ValueError("No valid product IDs found in product list")
    
    # Sort IDs for canonical ordering (ensures same signature regardless of input order)
    sorted_ids = sorted(product_ids)
    
    # Create deterministic signature
    signature_input = '|'.join(sorted_ids)
    signature = hashlib.sha256(signature_input.encode('utf-8')).hexdigest()
    
    return signature


def compute_signature_from_id_list(product_ids: List[str]) -> str:
    """
    Compute a signature directly from a list of product ID strings.
    
    Args:
        product_ids: List of product ID strings
        
    Returns:
        A hex-encoded SHA-256 hash string representing the unique product set
        
    Raises:
        ValueError: If the product ID list is empty
    """
    if not product_ids:
        raise ValueError("Cannot compute signature for empty product ID list")
    
    # Filter out None/empty values and convert to strings
    valid_ids = [str(pid) for pid in product_ids if pid is not None and str(pid).strip()]
    
    if not valid_ids:
        raise ValueError("No valid product IDs provided")
    
    # Sort for canonical ordering
    sorted_ids = sorted(valid_ids)
    
    # Create deterministic signature
    signature_input = '|'.join(sorted_ids)
    signature = hashlib.sha256(signature_input.encode('utf-8')).hexdigest()
    
    return signature


def validate_signature(signature: Optional[str]) -> bool:
    """
    Validate that a signature string is properly formatted.
    
    Args:
        signature: The signature string to validate
        
    Returns:
        True if the signature is valid, False otherwise
    """
    if not signature:
        return False
    
    if not isinstance(signature, str):
        return False
    
    # SHA-256 hex digest should be exactly 64 characters
    if len(signature) != 64:
        return False
    
    # Should only contain hex characters
    try:
        int(signature, 16)
        return True
    except ValueError:
        return False