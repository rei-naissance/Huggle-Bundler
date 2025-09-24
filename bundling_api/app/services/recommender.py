from collections import defaultdict
from datetime import datetime, timezone
from typing import List, Dict, Any

from dateutil import parser as date_parser
from sqlalchemy.orm import Session

from ..schemas.bundle import ProductIn, BundleCreate
from ..utils.text import oxford_join
from ..clients.inventory import fetch_products_for_store
from .ai import maybe_enhance_bundle_text
from ..repositories.bundles import bundle_exists_for_products
from ..utils.text import parse_tags_str as __parse_tags


def _safe_parse_dt(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return date_parser.parse(str(value))
    except Exception:
        return None


def recommend_bundles(db: Session, store_id: str, num_bundles: int = 3) -> List[BundleCreate]:
    products_raw = fetch_products_for_store(db, store_id)
    
    def product_ids_from_bundle(ps: List[ProductIn]) -> List[str]:
        """Extract product IDs from a list of ProductIn objects."""
        return [p.id for p in ps]

    # Normalize into ProductIn
    products: List[ProductIn] = []
    for p in products_raw:
        expires_on = _safe_parse_dt(p.get("expiresOn"))
        # Treat -infinity or missing as far future so they don't crowd expiring items
        if expires_on is None or (isinstance(expires_on, datetime) and expires_on.year < 1900):
            expires_on = datetime(9999, 1, 1, tzinfo=timezone.utc)
        product = ProductIn(
            id=str(p.get("id")),
            name=p.get("name") or "Unnamed",
            product_type=p.get("productType") or None,
            expires_on=expires_on,
            stock=int(p.get("stock") or 0),
            tags=__parse_tags(p.get("tags")),
        )
        products.append(product)

    if not products:
        return []

    # Group by product_type (fallback to 'Misc')
    buckets: Dict[str, List[ProductIn]] = defaultdict(list)
    for p in products:
        group = p.product_type or (p.tags[0] if p.tags else "Misc")
        buckets[group].append(p)

    # Sort each bucket by expiry (earliest first), then by low stock
    for group, items in buckets.items():
        buckets[group] = sorted(items, key=lambda x: (x.expires_on or datetime.max, x.stock))

    # Rank buckets by the earliest expiry inside each bucket
    ranked_groups = sorted(
        buckets.items(),
        key=lambda kv: (kv[1][0].expires_on or datetime.max),
    )

    # Create up to num_bundles candidates
    bundles: List[BundleCreate] = []
    for group_name, items in ranked_groups[: max(num_bundles * 2, num_bundles)]:
        # Select top 2-3 items for the bundle, prefer those expiring soon
        chosen = items[:3] if len(items) >= 3 else items[:2] if len(items) >= 2 else items[:1]
        if len(chosen) < 2:
            # skip bundles with fewer than 2 items (can relax if needed)
            continue
        stock = min([p.stock for p in chosen]) if chosen else 0

        name = f"{group_name} Essentials Pack"
        product_names = [p.name for p in chosen]
        description = f"Includes {oxford_join(product_names)}."

        # Optionally enhance with AI
        enhanced = maybe_enhance_bundle_text(name, product_names, stock)
        if enhanced:
            name, description = enhanced

        candidate = BundleCreate(
            store_id=store_id,
            name=name,
            description=description,
            products=chosen,
            images=[],
            stock=stock,
        )
        
        # Check if bundle with these products already exists
        product_ids = product_ids_from_bundle(candidate.products)
        if not bundle_exists_for_products(db, store_id, product_ids):
            bundles.append(candidate)
            
        if len(bundles) >= num_bundles:
            break

    # Top-up if fewer than requested
    if len(bundles) < num_bundles:
        pool = [p for items in buckets.values() for p in items]
        pool = sorted(pool, key=lambda x: (x.expires_on or datetime.max, x.stock))
        i = 0
        while len(bundles) < num_bundles and i + 1 < len(pool):
            chosen = [pool[i], pool[i+1]]
            product_ids = product_ids_from_bundle(chosen)
            
            # Skip if bundle with these products already exists
            if bundle_exists_for_products(db, store_id, product_ids):
                i += 2
                continue
                
            stock = min([p.stock for p in chosen]) if chosen else 0
            name = f"Quick Saver Pack"
            product_names = [p.name for p in chosen]
            description = f"Includes {oxford_join(product_names)}."
            bundles.append(BundleCreate(
                store_id=store_id,
                name=name,
                description=description,
                products=chosen,
                images=[],
                stock=stock,
            ))
            i += 2

    return bundles
