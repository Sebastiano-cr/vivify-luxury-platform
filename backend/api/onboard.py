import json
import logging
from datetime import datetime, timezone
from uuid import uuid4
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ..services.browser_agent import BrowserAutomationService
from ..services.trends import add_signal
from ..storage.db import fetchone, execute
from ..storage.hashchain import append_jewel_entry
from ..models.enums import MetalType, GemType, JewelStatus
from ..api.jewels import _row_to_jewel

logger = logging.getLogger("vivify.onboard")
router = APIRouter(prefix="/onboard", tags=["onboarding"])


def _create_jewel_from_dict(data: dict) -> dict:
    metal_str = data.get("metal", "ouro_18k").lower().replace(" ", "_")
    try:
        metal = MetalType(metal_str)
    except ValueError:
        metal = MetalType.OURO_18K

    gem_str = data.get("gemstones", [])
    if isinstance(gem_str, str):
        gem_list = [g.strip().lower() for g in gem_str.split(",") if g.strip()]
    else:
        gem_list = gem_str
    gemstones = []
    for g in gem_list:
        try:
            gemstones.append(GemType(g.lower()))
        except ValueError:
            pass

    weight = float(data.get("weight_grams", 1.0))
    name = (data.get("name") or "Joia Importada").strip()[:200]
    origin = data.get("origin") or data.get("sku") or ""
    description = data.get("description") or ""
    price = data.get("price")

    jewel_id = str(uuid4())
    metadata = {
        "action": "importacao_browser",
        "jewel_id": jewel_id,
        "name": name,
        "metal": metal.value,
        "gemstones": [g.value for g in gemstones],
        "weight_grams": weight,
        "origin": origin,
        "price": price,
        "source_url": data.get("source_url"),
    }
    entry_hash = append_jewel_entry(
        event_type="vivify.jewel.imported",
        jewel_id=jewel_id,
        metadata=metadata,
    )
    now = datetime.now(timezone.utc).isoformat()
    qr_code_url = f"/vivify/verify/{jewel_id}"

    execute(
        """INSERT INTO jewels (id, name, metal, gemstones, weight_grams, origin, status,
           hash_chain_entry_hash, qr_code_url, description, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            jewel_id,
            name,
            metal.value,
            json.dumps([g.value for g in gemstones]),
            weight,
            origin,
            JewelStatus.CADASTRADA.value,
            entry_hash,
            qr_code_url,
            description,
            now,
            now,
        ),
    )

    row = fetchone("SELECT * FROM jewels WHERE id = ?", (jewel_id,))
    return _row_to_jewel(row).model_dump(mode="json")


@router.post("/url")
async def onboard_from_url(url: str = Query(..., description="URL do catálogo da joalheria")):
    browser = BrowserAutomationService(headless=True)
    products = await browser.extract_catalog(url)
    if not products:
        raise HTTPException(status_code=400, detail="Nenhum produto encontrado ou site inacessível")

    imported = 0
    errors = []
    for product in products:
        try:
            product["source_url"] = url
            _create_jewel_from_dict(product)
            imported += 1
        except Exception as e:
            errors.append(f"{product.get('name', '?')}: {e}")
            logger.warning("Failed to import product %s: %s", product.get("name"), e)

    add_signal(
        handle="vivify_onboarding",
        platform="web",
        text=f"Importados {imported} produtos de {url} via browser-use",
        topics=["onboarding", "browser-use", "importacao"],
    )

    return {
        "status": "success",
        "url": url,
        "imported": imported,
        "total": len(products),
        "errors": errors[:10],
    }


@router.post("/monitor")
async def monitor_competitor(url: str = Query(..., description="URL do concorrente")):
    browser = BrowserAutomationService(headless=True)
    data = await browser.monitor_competitor(url)

    products = data.get("products", [])
    for p in products:
        add_signal(
            handle="vivify_competitor",
            platform="web",
            text=f"Concorrente {url}: {p.get('name', '?')} por {p.get('price', '?')}",
            topics=["competitor", "price", "monitoring"],
        )

    return {
        "status": "success",
        "url": url,
        "products_found": len(products),
        "products": products,
        "source": "browser-use",
    }


@router.post("/checkout-test")
async def test_checkout(
    url: str = Query(..., description="URL da loja"),
    product_ref: str = Query(..., description="ID ou nome do produto"),
):
    browser = BrowserAutomationService(headless=True)
    result = await browser.test_checkout(url, product_ref)

    append_jewel_entry(
        event_type="vivify.checkout_test",
        jewel_id="checkout_test",
        metadata={"url": url, "product_ref": product_ref, "result": result},
    )

    return {
        "status": "checkout_test",
        "url": url,
        "product_ref": product_ref,
        "result": result,
        "source": "browser-use",
    }
