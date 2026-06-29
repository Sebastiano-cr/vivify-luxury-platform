"""Simple event bus — dispatches product events to omnichannel channels."""
import json
import logging
from typing import Any, Callable, Coroutine

logger = logging.getLogger("vivify.event_bus")

_handlers: dict[str, list[Callable[..., Coroutine]]] = {}


def on(event: str):
    def decorator(fn: Callable[..., Coroutine]):
        _handlers.setdefault(event, []).append(fn)
        return fn
    return decorator


async def emit(event: str, **data):
    for handler in _handlers.get(event, []):
        try:
            await handler(**data)
        except Exception as e:
            logger.warning("Event handler %s for %s failed: %s", handler.__name__, event, e)


async def on_product_created(product_id: str):
    from .omnichannel import list_channels, sync_product_to_channel
    channels = list_channels()
    for ch in channels:
        if ch.get("active") and ch.get("type") in ("web", "whatsapp", "wacli", "instagram"):
            try:
                await sync_product_to_channel(product_id, ch["id"])
            except Exception as e:
                logger.warning("Auto-sync to %s failed: %s", ch["id"], e)


async def on_product_updated(product_id: str):
    from .omnichannel import get_sync_status, sync_product_to_channel
    syncs = get_sync_status(product_id=product_id)
    seen = set()
    for s in syncs:
        ch_id = s.get("channel_id")
        if ch_id and ch_id not in seen:
            seen.add(ch_id)
            try:
                await sync_product_to_channel(product_id, ch_id)
            except Exception as e:
                logger.warning("Re-sync to %s failed: %s", ch_id, e)


@on("jewel.sold")
async def on_jewel_sold(jewel_id: str, channel: str = "marketplace", tax: float = 0.0):
    from ..storage.db import fetchone
    from .ledger_client import LedgerClient

    row = fetchone("SELECT name, price FROM jewels WHERE id = ?", (jewel_id,))
    if not row:
        logger.warning("jewel.sold for unknown jewel %s", jewel_id)
        return
    price = row["price"] or 0
    ledger = LedgerClient()
    try:
        result = await ledger.record_sale(
            jewel_name=row["name"],
            channel=channel,
            price=price,
            cost=0,
            tax=tax,
        )
        logger.info("Ledger txn recorded for %s: %s", jewel_id, result.get("id"))
    except Exception as e:
        logger.error("Failed to record sale in ledger: %s", e)
