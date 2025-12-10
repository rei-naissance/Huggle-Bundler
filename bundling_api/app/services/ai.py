import json
import re
from typing import Tuple

import httpx

from ..config import settings
from ..utils.dates import parse_expiry as _safe_parse_dt
from ..schemas.bundle import ProductIn, BundleCreate
from ..clients.inventory import fetch_products_for_store
from datetime import datetime, timezone
from ..utils.text import parse_tags_str as __parse_tags
from ..repositories.bundles import bundle_exists_for_products


def _extract_json_object(text: str) -> dict | None:
    """Try to parse a JSON object from a string, handling code fences or extra text."""
    if not isinstance(text, str):
        return None
    # Fast path
    try:
        return json.loads(text)
    except Exception:
        pass
    # Strip backticks fences if present - fix the regex
    text2 = text.strip()
    if text2.startswith("```"):
        # Remove starting ```json and ending ```
        text2 = re.sub(r"^```(?:json)?\s*\n", "", text2, flags=re.IGNORECASE | re.MULTILINE)
        text2 = re.sub(r"\n?```\s*$", "", text2, flags=re.MULTILINE)
        text2 = text2.strip()
        try:
            return json.loads(text2)
        except Exception:
            pass
    # Fallback: find first {...} block
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None


def _openrouter_generate(name_hint: str, product_names: list[str], stock: int) -> Tuple[str, str] | None:
    if not settings.openrouter_api_key:
        return None
    # Default to the free DeepSeek chat model if unspecified
    model = settings.openrouter_model or "deepseek/deepseek-chat-v3.1:free"
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        # Optional headers that some OpenRouter setups recommend
        "HTTP-Referer": "http://localhost",  # adjust in production
        "X-Title": "Bundling API",
    }
    system = (
        "You name and describe retail product bundles succinctly. "
        "Return a compact JSON object with keys 'name' and 'description'."
    )
    user = (
        "Propose an improved, catchy yet honest bundle name and a single-sentence description.\n"
        f"Current name: {name_hint}\n"
        f"Products: {', '.join(product_names)}\n"
        f"Stock (min across items): {stock}\n"
        "Respond ONLY with JSON: {\"name\": string, \"description\": string}."
    )
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.7,
    }
    try:
        resp = httpx.post(url, headers=headers, json=data, timeout=httpx.Timeout(10.0))
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        payload = _extract_json_object(content)
        if not payload:
            return None
        name = str(payload.get("name") or "").strip()
        desc = str(payload.get("description") or "").strip()
        if name and desc:
            return name, desc
    except Exception:
        return None
    return None


def _groq_generate(name_hint: str, product_names: list[str], stock: int) -> Tuple[str, str] | None:
    if not settings.groq_api_key:
        return None
    model = settings.groq_model  # require explicit model for reliability
    if not model:
        # If no model is configured, skip rather than guess
        return None
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json",
    }
    system = (
        "You name and describe retail product bundles succinctly. "
        "Return a compact JSON object with keys 'name' and 'description'."
    )
    user = (
        "Propose an improved, catchy yet honest bundle name and a single-sentence description.\n"
        f"Current name: {name_hint}\n"
        f"Products: {', '.join(product_names)}\n"
        f"Stock (min across items): {stock}\n"
        "Respond ONLY with JSON: {\"name\": string, \"description\": string}."
    )
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.7,
    }
    try:
        resp = httpx.post(url, headers=headers, json=data, timeout=httpx.Timeout(10.0))
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        payload = _extract_json_object(content)
        if not payload:
            return None
        name = str(payload.get("name") or "").strip()
        desc = str(payload.get("description") or "").strip()
        if name and desc:
            return name, desc
    except Exception:
        return None
    return None


def maybe_enhance_bundle_text(name_hint: str, product_names: list[str], stock: int) -> Tuple[str, str] | None:
    """
    Try to get an AI-improved (name, description) with prioritized providers:
    1) Groq (fast path)
    2) OpenRouter (fallback)
    Returns None if both fail/misconfigured.
    If AI_PROVIDER is explicitly set, use that order first, then the other provider as fallback.
    """
    provider = (settings.ai_provider or "").lower().strip()
    order = ["groq", "openrouter"]
    if provider == "openrouter":
        order = ["openrouter", "groq"]
    for p in order:
        if p == "groq":
            res = _groq_generate(name_hint, product_names, stock)
            if res:
                return res
        elif p == "openrouter":
            res = _openrouter_generate(name_hint, product_names, stock)
            if res:
                return res
    return None


def _format_product_catalog(products: list[dict]) -> list[str]:
    lines: list[str] = []
    now = datetime.now(timezone.utc)
    for p in products:
        pid = str(p.get("id"))
        name = p.get("name") or "Unnamed"
        ptype = p.get("productType") or "unknown"
        stock = int(p.get("stock") or 0)
        tags = str(p.get("tags") or "")
        exp = _safe_parse_dt(p.get("expiresOn"))
        if exp is None or (isinstance(exp, datetime) and exp.year < 1900):
            days = 36500
        else:
            delta = exp - now
            days = max(int(delta.total_seconds() // 86400), -1)
        lines.append(f"{pid} | {name} | type:{ptype} | stock:{stock} | expires_in_days:{days} | tags:{tags}")
    return lines


def _openrouter_generate_bundles(catalog_lines: list[str], num_bundles: int) -> list[dict] | None:
    import logging
    logger = logging.getLogger(__name__)
    
    if not settings.openrouter_api_key:
        logger.warning("🚫 OpenRouter API key not configured")
        return None
        
    model = settings.openrouter_model or "deepseek/deepseek-chat-v3.1:free"
    # Updated OpenRouter API endpoint
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    logger.info(f"🔗 OpenRouter request: model={model}, url={url}")
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "Bundling API",
    }
    system = (
        "You create retail product bundles to reduce waste and increase sales. "
        "Only use product IDs from the provided catalog. Prioritize items expiring soon. "
        "Avoid zero-stock items. Bundle size: 2-5 items. Output JSON only."
    )
    user = (
        "Product Catalog (one per line):\n" + "\n".join(catalog_lines) + "\n\n" +
        f"Create up to {num_bundles} bundles as JSON: {{\"bundles\":[{{\"name\":str,\"description\":str,\"product_ids\":[str,...]}}...]}}"
    )
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.6,
    }
    try:
        resp = httpx.post(url, headers=headers, json=data, timeout=httpx.Timeout(12.0))
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        logger.debug(f"💬 OpenRouter response content: {content[:500]}...")
        
        payload = _extract_json_object(content) or {}
        logger.debug(f"📦 OpenRouter parsed payload: {payload}")
        
        bundles = payload.get("bundles") or []
        logger.info(f"🔗 OpenRouter returned {len(bundles)} bundles")
        
        if isinstance(bundles, list):
            return bundles
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        if hasattr(e, 'response'):
            try:
                response_text = e.response.text if hasattr(e.response, 'text') else str(e.response.content)
                logger.error(f"💥 OpenRouter API call failed: {type(e).__name__}: {str(e)}")
                logger.error(f"📜 Response content: {response_text[:500]}...")
            except:
                logger.error(f"💥 OpenRouter API call failed: {type(e).__name__}: {str(e)}")
        else:
            logger.error(f"💥 OpenRouter API call failed: {type(e).__name__}: {str(e)}")
        return None
    return None


def _groq_generate_bundles(catalog_lines: list[str], num_bundles: int, suggestions: str = "") -> list[dict] | None:
    import logging
    logger = logging.getLogger(__name__)
    
    if not settings.groq_api_key:
        logger.warning("🚫 Groq API key not configured")
        return None
        
    model = settings.groq_model
    if not model:
        logger.warning("⚠️ Groq model not configured in settings")
        return None
        
    logger.info(f"🎆 Groq request: model={model}")
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json",
    }
    system = (
        "You create NEW retail product bundles to reduce waste and increase sales. "
        "IMPORTANT: Only suggest combinations that are NOT in the exclusion list. "
        "Only use product IDs from the provided catalog. Prioritize items expiring soon. "
        "Avoid zero-stock items. Bundle size: 2-3 items preferred. Output valid JSON only."
    )
    user = (
        "Product Catalog (one per line):\n" + "\n".join(catalog_lines) + "\n\n" +
        suggestions +
        f"\nCreate exactly {num_bundles} bundles using the suggested combinations as JSON: {{\"bundles\":[{{\"name\":str,\"description\":str,\"product_ids\":[str,...]}}...]}}"
    )
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.6,
    }
    try:
        resp = httpx.post(url, headers=headers, json=data, timeout=httpx.Timeout(12.0))
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        logger.debug(f"💬 Groq response content: {content[:500]}...")
        
        payload = _extract_json_object(content) or {}
        logger.debug(f"📦 Groq parsed payload: {payload}")
        
        bundles = payload.get("bundles") or []
        logger.info(f"🎆 Groq returned {len(bundles)} bundles")
        
        if isinstance(bundles, list) and len(bundles) > 0:
            return bundles
        else:
            logger.warning("⚠️ Groq returned empty or invalid bundles list")
            return None
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        if hasattr(e, 'response'):
            try:
                response_text = e.response.text if hasattr(e.response, 'text') else str(e.response.content)
                logger.error(f"💥 Groq API call failed: {type(e).__name__}: {str(e)}")
                logger.error(f"📜 Response content: {response_text[:500]}...")
            except:
                logger.error(f"💥 Groq API call failed: {type(e).__name__}: {str(e)}")
        else:
            logger.error(f"💥 Groq API call failed: {type(e).__name__}: {str(e)}")
        return None
    return None


def generate_bundles_for_store(db, store_id: str, num_bundles: int = 3) -> list[BundleCreate]:
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"🏪 generate_bundles_for_store called with store_id='{store_id}', num_bundles={num_bundles}")
    
    if not store_id:
        logger.warning("❌ No store_id provided, returning empty list")
        return []
        
    logger.info(f"📡 Fetching products for store: {store_id}")
    products_raw = fetch_products_for_store(db, store_id)
    logger.info(f"🛍️ Fetched {len(products_raw)} raw products from store {store_id}")
    # Filter out suspended products defensively if present in payload
    before = len(products_raw)
    products_raw = [p for p in products_raw if not bool(p.get("is_suspended"))]
    removed = before - len(products_raw)
    if removed:
        logger.info(f"🚫 Excluded {removed} suspended products from generation pool")

    def extract_product_ids(products) -> list[str]:
        """Extract product IDs from various product representations."""
        if isinstance(products, list):
            ids = []
            for item in products:
                if isinstance(item, ProductIn):
                    ids.append(item.id)
                elif isinstance(item, dict) and "id" in item:
                    ids.append(str(item["id"]))
                elif isinstance(item, str):
                    ids.append(item)
            return ids
        return []
    # Sort by earliest expiry and limit catalog size to keep prompt manageable
    now = datetime.now(timezone.utc)
    def expiry_key(p):
        dt = _safe_parse_dt(p.get("expiresOn"))
        if dt is None or (isinstance(dt, datetime) and dt.year < 1900):
            return datetime(9999, 1, 1, tzinfo=timezone.utc)
        return dt
    products_raw = sorted(products_raw, key=expiry_key)[:200]
    logger.info(f"📋 Sorted and limited to {len(products_raw)} products for catalog")
    
    if len(products_raw) == 0:
        logger.warning("⚠️ No products found for store after filtering, returning empty list")
        return []

    catalog_lines = _format_product_catalog(products_raw)
    logger.info(f"📝 Created catalog with {len(catalog_lines)} product lines")
    logger.debug(f"Sample catalog lines: {catalog_lines[:3] if catalog_lines else 'None'}")
    
    provider = (settings.ai_provider or "").lower().strip()
    logger.info(f"🤖 AI Provider setting: '{provider}' (from settings.ai_provider)")
    
    # Instead of exclusions, let's find and suggest AVAILABLE combinations
    from itertools import combinations
    from ..repositories.bundles import bundle_exists_for_products
    
    product_ids = [str(p.get("id")) for p in products_raw]
    all_available = []
    
    # Find available 2-product combinations first
    logger.info("🔍 Checking 2-product combinations...")
    for combo in combinations(product_ids, 2):
        combo_list = list(combo)
        if not bundle_exists_for_products(db, store_id, combo_list):
            names = []
            for pid in combo_list:
                for p in products_raw:
                    if str(p.get("id")) == pid:
                        names.append(p.get("name", "Unknown"))
                        break
            if len(names) == 2:
                all_available.append({"ids": combo_list, "names": names, "size": 2})
    
    logger.info(f"📍 Found {len(all_available)} available 2-product combinations")
    
    # If no 2-product combos available, try 3-product combinations
    if len(all_available) == 0 and len(products_raw) >= 3:
        logger.info("🔍 No 2-product combos available, checking 3-product combinations...")
        for combo in combinations(product_ids, 3):
            combo_list = list(combo)
            if not bundle_exists_for_products(db, store_id, combo_list):
                names = []
                for pid in combo_list:
                    for p in products_raw:
                        if str(p.get("id")) == pid:
                            names.append(p.get("name", "Unknown"))
                            break
                if len(names) == 3:
                    all_available.append({"ids": combo_list, "names": names, "size": 3})
        logger.info(f"📍 Found {len(all_available)} available 3-product combinations")
    
    # If still no combos, try 4-product combinations
    if len(all_available) == 0 and len(products_raw) >= 4:
        logger.info("🔍 No 2 or 3-product combos available, checking 4-product combinations...")
        for combo in combinations(product_ids, 4):
            combo_list = list(combo)
            if not bundle_exists_for_products(db, store_id, combo_list):
                names = []
                for pid in combo_list:
                    for p in products_raw:
                        if str(p.get("id")) == pid:
                            names.append(p.get("name", "Unknown"))
                            break
                if len(names) == 4:
                    all_available.append({"ids": combo_list, "names": names, "size": 4})
        logger.info(f"📍 Found {len(all_available)} available 4-product combinations")
    
    # Create suggestions for AI - show up to 12 combinations
    suggestions = ""
    if all_available:
        logger.info(f"💡 Total available combinations: {len(all_available)}")
        suggestion_text = []
        max_suggestions = min(12, len(all_available))  # Increased from 4 to 12
        
        for combo in all_available[:max_suggestions]:
            combo_str = " + ".join([f"'{name}'" for name in combo['names']])
            id_str = ", ".join([pid[:8] for pid in combo['ids']])
            suggestion_text.append(f"{combo_str} (IDs: {id_str})")
        
        suggestions = f"\nSUGGESTED available combinations ({max_suggestions} of {len(all_available)}): {'; '.join(suggestion_text)}"
        logger.debug(f"💡 Suggestions: {suggestions[:300]}...")
    else:
        logger.warning("⚠️ No available combinations found for any size (2-4 products)")
        suggestions = "\nNo available product combinations found. All possible bundles may already exist."
    
    # Focus on Groq since it's working, disable OpenRouter for now due to API issues
    order = ["groq"] if settings.groq_api_key else []
    logger.info(f"🔄 Provider order: {order} (OpenRouter temporarily disabled due to API issues)")

    bundles_def: list[dict] | None = None
    for p in order:
        logger.info(f"🚀 Trying AI provider: {p}")
        if p == "groq":
            bundles_def = _groq_generate_bundles(catalog_lines, num_bundles, suggestions)
        elif p == "openrouter":
            bundles_def = _openrouter_generate_bundles(catalog_lines, num_bundles)
        
        if bundles_def:
            logger.info(f"✅ Provider {p} returned {len(bundles_def)} bundle definitions")
            break
        else:
            logger.warning(f"❌ Provider {p} returned no bundles")

    if not bundles_def:
        logger.warning("⚠️ No AI providers returned bundle definitions, will create simple bundles manually")
        bundles_def = []
        
        # Create simple manual bundles when AI fails
        logger.info("🔧 Creating manual bundles as AI fallback")
        if len(products_raw) >= 2:
            # Create basic 2-product bundles
            for i in range(0, min(len(products_raw), num_bundles * 2), 2):
                if i + 1 < len(products_raw):
                    p1, p2 = products_raw[i], products_raw[i + 1]
                    bundles_def.append({
                        "name": f"{p1.get('name', 'Product')} & {p2.get('name', 'Product')} Bundle",
                        "description": f"Great value bundle including {p1.get('name')} and {p2.get('name')}.",
                        "product_ids": [str(p1.get('id')), str(p2.get('id'))]
                    })
                    if len(bundles_def) >= num_bundles:
                        break
            logger.info(f"📦 Created {len(bundles_def)} manual bundle definitions")

    by_id = {str(p.get("id")): p for p in products_raw}
    logger.info(f"🖥️ Created product lookup with {len(by_id)} products by ID")
    
    results: list[BundleCreate] = []
    logger.info(f"🎨 Processing {len(bundles_def)} bundle definitions from AI")
    
    for i, b in enumerate(bundles_def):
        logger.debug(f"Processing bundle {i+1}/{len(bundles_def)}: {b.get('name', 'Unnamed')}")
        name = str(b.get("name") or "Unnamed Bundle").strip()
        desc = str(b.get("description") or "").strip() or None
        pids = b.get("product_ids") or b.get("products") or []
        # Normalize pids if given as objects
        normalized_ids: list[str] = []
        for item in pids:
            if isinstance(item, dict) and "id" in item:
                normalized_ids.append(str(item["id"]))
            elif isinstance(item, str):
                normalized_ids.append(item)
        # Map to ProductIn
        chosen_products: list[ProductIn] = []
        for pid in normalized_ids:
            pr = by_id.get(str(pid))
            if not pr:
                continue
            # Skip suspended items
            if bool(pr.get("is_suspended")):
                continue
            # Skip zero stock
            if int(pr.get("stock") or 0) <= 0:
                continue
            expires_on = _safe_parse_dt(pr.get("expiresOn"))
            if expires_on is None or (isinstance(expires_on, datetime) and expires_on.year < 1900):
                expires_on = datetime(9999, 1, 1, tzinfo=timezone.utc)
            chosen_products.append(ProductIn(
                id=str(pr.get("id")),
                name=pr.get("name") or "Unnamed",
                product_type=pr.get("productType") or None,
                expires_on=expires_on,
                stock=int(pr.get("stock") or 0),
                tags=__parse_tags(pr.get("tags")),
                price=float(pr.get("price") or 0.0),
                original_price=float(pr.get("originalPrice") or 0.0),
            ))
        # Ensure 2-5 items
        if len(chosen_products) < 2:
            continue
        stock = min([p.stock for p in chosen_products]) if chosen_products else 0
        candidate = BundleCreate(
            store_id=store_id,
            name=name,
            description=desc,
            products=chosen_products,
            images=[],
            stock=stock,
        )
        # Check if bundle with these products already exists
        product_ids = extract_product_ids(candidate.products)
        exists = bundle_exists_for_products(db, store_id, product_ids)
        logger.debug(f"Bundle '{name}' with products {product_ids}: exists={exists}")
        
        if not exists:
            results.append(candidate)
            logger.info(f"✅ Added bundle '{name}' to results ({len(results)}/{num_bundles})")
        else:
            logger.info(f"⚠️ Skipped duplicate bundle '{name}'")
            
        if len(results) >= num_bundles:
            logger.info(f"🏁 Reached target of {num_bundles} bundles, stopping processing")
            break

    logger.info(f"📊 Processed AI bundles, got {len(results)} valid candidates (requested: {num_bundles})")
    
    # Top-up to reach exactly num_bundles with last-resort pairs
    if len(results) < num_bundles:
        logger.info(f"🔄 Need to top-up bundles: have {len(results)}, need {num_bundles}. Using fallback pair generation.")
        # Flatten pool by earliest expiry
        pool_sorted = sorted(products_raw, key=expiry_key)
        logger.info(f"📋 Fallback pool has {len(pool_sorted)} products sorted by expiry")
        i = 0
        while len(results) < num_bundles and i + 1 < len(pool_sorted):
            pr1, pr2 = pool_sorted[i], pool_sorted[i+1]
            # skip zero stock
            if int(pr1.get("stock") or 0) <= 0:
                i += 1
                continue
            if int(pr2.get("stock") or 0) <= 0:
                i += 2
                continue
            # skip suspended
            if bool(pr1.get("is_suspended")):
                i += 1
                continue
            if bool(pr2.get("is_suspended")):
                i += 2
                continue
            # Check if bundle with these products already exists
            product_ids = [str(pr1.get("id")), str(pr2.get("id"))]
            exists = bundle_exists_for_products(db, store_id, product_ids)
            logger.debug(f"Fallback bundle check for products {product_ids}: exists={exists}")
            
            if exists:
                logger.debug(f"Skipping existing fallback bundle with products {product_ids}")
                i += 2
                continue
            def to_product_in(pr):
                exp = _safe_parse_dt(pr.get("expiresOn"))
                if exp is None or (isinstance(exp, datetime) and exp.year < 1900):
                    exp = datetime(9999, 1, 1, tzinfo=timezone.utc)
                return ProductIn(
                    id=str(pr.get("id")),
                    name=pr.get("name") or "Unnamed",
                    product_type=pr.get("productType") or None,
                    expires_on=exp,
                    stock=int(pr.get("stock") or 0),
                    tags=__parse_tags(pr.get("tags")),
                    price=float(pr.get("price") or 0.0),
                    original_price=float(pr.get("originalPrice") or 0.0),
                )
            chosen = [to_product_in(pr1), to_product_in(pr2)]
            stock = min([p.stock for p in chosen])
            candidate = BundleCreate(
                store_id=store_id,
                name="Quick Pair Pack",
                description=f"Includes {chosen[0].name} and {chosen[1].name}.",
                products=chosen,
                images=[],
                stock=stock,
            )
            product_ids = extract_product_ids(candidate.products)
            exists = bundle_exists_for_products(db, store_id, product_ids)
            
            if not exists:
                results.append(candidate)
                logger.info(f"✅ Added fallback bundle '{candidate.name}' ({len(results)}/{num_bundles})")
            else:
                logger.debug(f"Fallback bundle already exists, skipping")
            i += 2

    logger.info(f"🎉 Final result: returning {len(results)} bundles for store {store_id}")
    for i, result in enumerate(results):
        logger.info(f"  Bundle {i+1}: '{result.name}' with {len(result.products)} products")
    
    return results
