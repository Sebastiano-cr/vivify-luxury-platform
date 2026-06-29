"""WhatsApp Business API adapter for omnichannel catalog sync."""
import json
import logging
from typing import Any

import httpx

from .omnichannel import ChannelAdapter

logger = logging.getLogger("vivify.omnichannel.whatsapp")

WHATSAPP_API_BASE = "https://graph.facebook.com/v22.0"


class WhatsAppAdapter(ChannelAdapter):
    async def push_product(self, product: dict, config: dict) -> dict:
        phone_number_id = config.get("phone_number_id")
        token = config.get("token")
        if not phone_number_id or not token:
            return {"success": False, "error": "Missing phone_number_id or token"}

        marketplace_url = config.get("marketplace_url", "")
        product_url = f"{marketplace_url}/vivify/marketplace/{product['id']}" if marketplace_url else ""

        price = product.get("price", "")
        name = product.get("name", "Joia")
        description = product.get("description", "") or name

        template_body = (
            f"*{name}*\n{description}\n"
            + (f"💰 R$ {price}\n" if price else "")
            + (f"\n🔗 {product_url}" if product_url else "")
        )

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": config.get("target_phone", ""),
            "type": "text",
            "text": {"body": template_body[:4096]},
        }

        async with httpx.AsyncClient(timeout=15) as client:
            try:
                resp = await client.post(
                    f"{WHATSAPP_API_BASE}/{phone_number_id}/messages",
                    headers=headers,
                    json=payload,
                )
                data = resp.json()
                if resp.status_code != 200 and resp.status_code != 201:
                    logger.warning("WhatsApp API error: %s", data)
                    return {
                        "success": False,
                        "status": "error",
                        "message": data.get("error", {}).get("message", str(data)),
                    }
                external_id = data.get("messages", [{}])[0].get("id", "")
                return {"success": True, "status": "synced", "external_id": external_id, "message": "WhatsApp message sent"}
            except Exception as e:
                logger.warning("WhatsApp push failed: %s", e)
                return {"success": False, "status": "error", "message": str(e)}

    async def delete_product(self, external_id: str, config: dict) -> dict:
        return {"success": True, "status": "deleted", "message": "WhatsApp messages cannot be deleted via API"}

    async def health_check(self, config: dict) -> bool:
        token = config.get("token")
        phone_number_id = config.get("phone_number_id")
        if not token or not phone_number_id:
            return False
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                resp = await client.get(
                    f"{WHATSAPP_API_BASE}/{phone_number_id}",
                    headers=headers,
                )
                return resp.status_code == 200
            except Exception:
                return False
