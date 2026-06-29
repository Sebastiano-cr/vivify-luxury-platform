"""Instagram Catalog adapter for omnichannel — syncs products to Instagram Shopping catalog."""
import json
import logging
from typing import Any

import httpx

from .omnichannel import ChannelAdapter

logger = logging.getLogger("vivify.omnichannel.instagram")

GRAPH_API_BASE = "https://graph.facebook.com/v22.0"


class InstagramAdapter(ChannelAdapter):
    async def push_product(self, product: dict, config: dict) -> dict:
        catalog_id = config.get("catalog_id")
        token = config.get("token")
        if not catalog_id or not token:
            return {"success": False, "error": "Missing catalog_id or token in channel config"}

        name = product.get("name", "Joia")
        description = product.get("description", "") or name
        price = product.get("price", "")
        currency = config.get("currency", "BRL")
        image_url = product.get("image_url", "")
        sku = product.get("sku", f"VIVIFY-{product.get('id', '')}")
        url = product.get("url", "")

        payload = {
            "item_group_id": sku,
            "name": name[:100],
            "description": description[:1000],
            "image_url": image_url,
            "url": url,
            "retailer_id": sku,
            "retailer_product_group_id": sku,
            "availability": "in stock",
            "condition": "new",
        }

        if price:
            price_val = float(price)
            payload["price"] = f"{price_val:.2f}"
            payload["currency"] = currency

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        async with httpx.AsyncClient(timeout=15) as client:
            try:
                resp = await client.post(
                    f"{GRAPH_API_BASE}/{catalog_id}/products",
                    headers=headers,
                    json=payload,
                )
                data = resp.json()
                if resp.status_code not in (200, 201):
                    logger.warning("Instagram Catalog API error: %s", data)
                    return {
                        "success": False,
                        "status": "error",
                        "message": data.get("error", {}).get("message", str(data)),
                    }
                external_id = data.get("id", "")
                return {
                    "success": True,
                    "status": "synced",
                    "external_id": external_id,
                    "message": "Product synced to Instagram catalog",
                }
            except Exception as e:
                logger.warning("Instagram push failed: %s", e)
                return {"success": False, "status": "error", "message": str(e)}

    async def delete_product(self, external_id: str, config: dict) -> dict:
        token = config.get("token")
        if not token or not external_id:
            return {"success": False, "error": "Missing token or external_id"}
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                resp = await client.delete(
                    f"{GRAPH_API_BASE}/{external_id}",
                    headers=headers,
                )
                if resp.status_code == 200:
                    return {"success": True, "status": "deleted", "message": "Product removed from catalog"}
                data = resp.json()
                return {"success": False, "status": "error", "message": data.get("error", {}).get("message", str(data))}
            except Exception as e:
                return {"success": False, "status": "error", "message": str(e)}

    async def health_check(self, config: dict) -> bool:
        token = config.get("token")
        catalog_id = config.get("catalog_id")
        if not token or not catalog_id:
            return False
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                resp = await client.get(
                    f"{GRAPH_API_BASE}/{catalog_id}",
                    headers=headers,
                    params={"fields": "id,name"},
                )
                return resp.status_code == 200
            except Exception:
                return False
