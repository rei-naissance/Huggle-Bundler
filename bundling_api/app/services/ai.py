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
    # Strip backticks fences if present
    text2 = text.strip()
    if text2.startswith("```"):
        text2 = re.sub(r"^```(?:json)?\\n|```$", "", text2, flags=re.IGNORECASE | re.MULTILINE).strip()
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
    if not settings.openrouter_api_key:
        return None
    model = settings.openrouter_model or "deepseek/deepseek-chat-v3.1:free"
    url = "https://openrouter.ai/api/v1/chat/completions"
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
        payload = _extract_json_object(content) or {}
        bundles = payload.get("bundles") or []
        if isinstance(bundles, list):
            return bundles
    except Exception:
        return None
    return None


def _groq_generate_bundles(catalog_lines: list[str], num_bundles: int) -> list[dict] | None:
    if not settings.groq_api_key:
        return None
    model = settings.groq_model
    if not model:
        return None
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json",
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
        payload = _extract_json_object(content) or {}
        bundles = payload.get("bundles") or []
        if isinstance(bundles, list):
            return bundles
    except Exception:
        return None
    return None


def generate_bundles_for_store(db, store_id: str, num_bundles: int = 3) -> list[BundleCreate]:
    if not store_id:
        return []
    products_raw = fetch_products_for_store(db, store_id)

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

    catalog_lines = _format_product_catalog(products_raw)
    provider = (settings.ai_provider or "").lower().strip()
    # Prioritized provider order: Groq -> OpenRouter (unless explicitly set otherwise)
    order = ["groq", "openrouter"]
    if provider == "openrouter":
        order = ["openrouter", "groq"]

    bundles_def: list[dict] | None = None
    for p in order:
        if p == "groq":
            bundles_def = _groq_generate_bundles(catalog_lines, num_bundles)
        elif p == "openrouter":
            bundles_def = _openrouter_generate_bundles(catalog_lines, num_bundles)
        if bundles_def:
            break

    if not bundles_def:
        bundles_def = []

    by_id = {str(p.get("id")): p for p in products_raw}
    results: list[BundleCreate] = []
    for b in bundles_def:
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
        if not bundle_exists_for_products(db, store_id, product_ids):
            results.append(candidate)
        if len(results) >= num_bundles:
            break

    # Top-up to reach exactly num_bundles with last-resort pairs
    if len(results) < num_bundles:
        # Flatten pool by earliest expiry
        pool_sorted = sorted(products_raw, key=expiry_key)
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
            # Check if bundle with these products already exists
            product_ids = [str(pr1.get("id")), str(pr2.get("id"))]
            if bundle_exists_for_products(db, store_id, product_ids):
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
            if not bundle_exists_for_products(db, store_id, product_ids):
                results.append(candidate)
            i += 2

    return results
