"""Omnichannel — sincronização de catálogo com canais de venda externos."""
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from ..storage.db import execute, fetchone, fetchall

logger = logging.getLogger("vivify.omnichannel")


class ChannelAdapter(ABC):
    @abstractmethod
    async def push_product(self, product: dict, channel_config: dict) -> dict:
        ...

    @abstractmethod
    async def delete_product(self, external_id: str, channel_config: dict) -> dict:
        ...

    @abstractmethod
    async def health_check(self, channel_config: dict) -> bool:
        ...


def create_channel(tenant_id: str, channel_type: str, name: str, config: dict) -> str:
    cid = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    execute(
        "INSERT INTO channels (id, tenant_id, type, name, config, active, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, 1, ?, ?)",
        (cid, tenant_id, channel_type, name, json.dumps(config), now, now),
    )
    return cid


def update_channel(channel_id: str, name: str = None, config: dict = None, active: bool = None) -> bool:
    row = fetchone("SELECT id FROM channels WHERE id = ?", (channel_id,))
    if not row:
        return False
    now = datetime.now(timezone.utc).isoformat()
    if name is not None:
        execute("UPDATE channels SET name = ?, updated_at = ? WHERE id = ?", (name, now, channel_id))
    if config is not None:
        execute("UPDATE channels SET config = ?, updated_at = ? WHERE id = ?", (json.dumps(config), now, channel_id))
    if active is not None:
        execute("UPDATE channels SET active = ?, updated_at = ? WHERE id = ?", (1 if active else 0, now, channel_id))
    return True


def delete_channel(channel_id: str) -> bool:
    row = fetchone("SELECT id FROM channels WHERE id = ?", (channel_id,))
    if not row:
        return False
    execute("DELETE FROM channel_products WHERE channel_id = ?", (channel_id,))
    execute("DELETE FROM channels WHERE id = ?", (channel_id,))
    return True


def list_channels(tenant_id: str = None) -> list[dict]:
    if tenant_id:
        return fetchall(
            "SELECT id, tenant_id, type, name, active, created_at, updated_at FROM channels WHERE tenant_id = ? ORDER BY created_at DESC",
            (tenant_id,),
        )
    return fetchall(
        "SELECT id, tenant_id, type, name, active, created_at, updated_at FROM channels ORDER BY created_at DESC"
    )


def get_channel(channel_id: str) -> Optional[dict]:
    row = fetchone("SELECT * FROM channels WHERE id = ?", (channel_id,))
    if row:
        row["config"] = json.loads(row["config"]) if isinstance(row["config"], str) else row["config"]
    return row


async def sync_product_to_channel(product_id: str, channel_id: str) -> dict:
    channel = get_channel(channel_id)
    if not channel or not channel.get("active"):
        return {"success": False, "error": "Channel not found or inactive"}

    product = fetchone("SELECT * FROM jewels WHERE id = ?", (product_id,))
    if not product:
        return {"success": False, "error": "Product not found"}

    adapter = _get_adapter(channel["type"])
    if not adapter:
        return {"success": False, "error": f"No adapter for channel type: {channel['type']}"}

    try:
        result = await adapter.push_product(dict(product), channel["config"])
        external_id = result.get("external_id", "")
        now = datetime.now(timezone.utc).isoformat()
        existing = fetchone(
            "SELECT id FROM channel_products WHERE channel_id = ? AND product_id = ?",
            (channel_id, product_id),
        )
        if existing:
            execute(
                "UPDATE channel_products SET external_id = ?, sync_status = ?, last_sync = ? WHERE id = ?",
                (external_id, result.get("status", "synced"), now, existing["id"]),
            )
        else:
            cpid = str(uuid4())
            execute(
                "INSERT INTO channel_products (id, channel_id, product_id, external_id, sync_status, last_sync) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (cpid, channel_id, product_id, external_id, result.get("status", "synced"), now),
            )
        _log_sync(channel_id, "push", "success", 1, result.get("message", ""))
        return {"success": True, "external_id": external_id, "status": result.get("status", "synced")}
    except Exception as e:
        logger.warning("Sync failed for product %s to channel %s: %s", product_id, channel_id, e)
        _log_sync(channel_id, "push", "error", 0, str(e))
        return {"success": False, "error": str(e)}


def get_sync_status(product_id: str = None, channel_id: str = None) -> list[dict]:
    if product_id and channel_id:
        return fetchall(
            "SELECT * FROM channel_products WHERE product_id = ? AND channel_id = ?",
            (product_id, channel_id),
        )
    elif product_id:
        return fetchall(
            "SELECT * FROM channel_products WHERE product_id = ?", (product_id,)
        )
    elif channel_id:
        return fetchall(
            "SELECT * FROM channel_products WHERE channel_id = ?", (channel_id,)
        )
    return fetchall("SELECT * FROM channel_products ORDER BY last_sync DESC")


def get_sync_logs(channel_id: str = None, limit: int = 50) -> list[dict]:
    if channel_id:
        return fetchall(
            "SELECT * FROM sync_log WHERE channel_id = ? ORDER BY created_at DESC LIMIT ?",
            (channel_id, limit),
        )
    return fetchall("SELECT * FROM sync_log ORDER BY created_at DESC LIMIT ?", (limit,))


def _get_adapter(channel_type: str) -> Optional[ChannelAdapter]:
    if channel_type == "whatsapp":
        from .omnichannel_whatsapp import WhatsAppAdapter
        return WhatsAppAdapter()
    if channel_type == "wacli":
        from .omnichannel_wacli_adapter import WacliWhatsAppAdapter
        return WacliWhatsAppAdapter()
    if channel_type == "instagram":
        from .omnichannel_instagram import InstagramAdapter
        return InstagramAdapter()
    if channel_type == "web":
        from .omnichannel_web import WebAdapter
        return WebAdapter()
    return None


def _log_sync(channel_id: str, action: str, status: str, product_count: int, message: str):
    now = datetime.now(timezone.utc).isoformat()
    execute(
        "INSERT INTO sync_log (id, channel_id, action, status, product_count, message, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (str(uuid4()), channel_id, action, status, product_count, message[:500], now),
    )
