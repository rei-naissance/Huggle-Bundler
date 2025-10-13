"""
Bundle Pricing Service

Handles pricing calculations for bundles, including:
- Total price calculation from individual products
- Bundle discount application
- Savings calculation
"""

import logging
from typing import List, Dict, Optional
from decimal import Decimal, ROUND_HALF_UP
from ..schemas.bundle import ProductIn, BundleCreate

logger = logging.getLogger(__name__)


class BundlePricingCalculator:
    """Calculate pricing for bundles based on products and discount rules."""
    
    # Default bundle discount percentages based on bundle size
    DEFAULT_DISCOUNTS = {
        2: 5.0,   # 5% discount for 2 items
        3: 10.0,  # 10% discount for 3 items
        4: 15.0,  # 15% discount for 4 items
        5: 20.0,  # 20% discount for 5+ items
    }
    
    def __init__(self, custom_discounts: Optional[Dict[int, float]] = None):
        """
        Initialize pricing calculator.
        
        Args:
            custom_discounts: Custom discount percentages by bundle size
        """
        self.discount_rates = custom_discounts or self.DEFAULT_DISCOUNTS
    
    def calculate_total_price(self, products: List[ProductIn]) -> float:
        """Calculate total price from individual product prices."""
        return sum(product.price for product in products)
    
    def calculate_bundle_discount_percentage(self, products: List[ProductIn]) -> float:
        """
        Calculate discount percentage based on number of products.
        
        Args:
            products: List of products in the bundle
            
        Returns:
            Discount percentage (0-100)
        """
        product_count = len(products)
        
        if product_count < 2:
            return 0.0
        
        # Get discount for exact count, or use highest discount for 5+ items
        if product_count in self.discount_rates:
            return self.discount_rates[product_count]
        elif product_count >= 5:
            return self.discount_rates[5]
        else:
            return 0.0
    
    def calculate_discounted_price(self, total_price: float, discount_percentage: float) -> float:
        """Calculate discounted price with proper rounding."""
        if discount_percentage <= 0:
            return total_price
            
        discount_decimal = Decimal(str(discount_percentage)) / Decimal('100')
        price_decimal = Decimal(str(total_price))
        
        discounted = price_decimal * (Decimal('1') - discount_decimal)
        
        # Round to 2 decimal places
        return float(discounted.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
    
    def calculate_savings_amount(self, total_price: float, discounted_price: float) -> float:
        """Calculate savings amount."""
        savings = Decimal(str(total_price)) - Decimal(str(discounted_price))
        return float(savings.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
    
    def calculate_bundle_pricing(self, products: List[ProductIn]) -> Dict[str, Optional[float]]:
        """
        Calculate complete pricing information for a bundle.
        
        Args:
            products: List of products in the bundle
            
        Returns:
            Dictionary with pricing information:
            - total_price: Sum of individual product prices
            - discount_percentage: Applied discount percentage
            - discounted_price: Final bundle price after discount
            - savings_amount: Amount saved compared to individual prices
        """
        if not products:
            logger.warning("Cannot calculate pricing for empty product list")
            return {
                'total_price': 0.0,
                'discount_percentage': None,
                'discounted_price': None,
                'savings_amount': None
            }
        
        try:
            # Calculate total price
            total_price = self.calculate_total_price(products)
            
            # Calculate discount percentage
            discount_percentage = self.calculate_bundle_discount_percentage(products)
            
            # Calculate discounted price and savings
            discounted_price = None
            savings_amount = None
            
            if discount_percentage > 0:
                discounted_price = self.calculate_discounted_price(total_price, discount_percentage)
                savings_amount = self.calculate_savings_amount(total_price, discounted_price)
            
            pricing_info = {
                'total_price': total_price,
                'discount_percentage': discount_percentage if discount_percentage > 0 else None,
                'discounted_price': discounted_price,
                'savings_amount': savings_amount
            }
            
            logger.info(f"Calculated bundle pricing for {len(products)} products: {pricing_info}")
            
            return pricing_info
            
        except Exception as e:
            logger.error(f"Error calculating bundle pricing: {e}")
            return {
                'total_price': 0.0,
                'discount_percentage': None,
                'discounted_price': None,
                'savings_amount': None
            }


def calculate_bundle_pricing(products: List[ProductIn], custom_discounts: Optional[Dict[int, float]] = None) -> Dict[str, Optional[float]]:
    """
    Convenience function to calculate bundle pricing.
    
    Args:
        products: List of products in the bundle
        custom_discounts: Optional custom discount rates
        
    Returns:
        Dictionary with pricing information
    """
    calculator = BundlePricingCalculator(custom_discounts)
    return calculator.calculate_bundle_pricing(products)


def apply_pricing_to_bundle(bundle_data: BundleCreate, pricing_info: Dict[str, Optional[float]]) -> BundleCreate:
    """
    Apply calculated pricing to a BundleCreate object.
    
    Args:
        bundle_data: Original bundle data
        pricing_info: Calculated pricing information
        
    Returns:
        Updated BundleCreate object with pricing information
    """
    # Create a dict from the bundle data and update it with pricing
    bundle_dict = bundle_data.model_dump()
    bundle_dict.update(pricing_info)
    
    return BundleCreate(**bundle_dict)