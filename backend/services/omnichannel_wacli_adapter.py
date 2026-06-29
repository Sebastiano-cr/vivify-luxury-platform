"""WACli-based WhatsApp adapter for omnichannel — sends product catalog via WhatsApp Web."""
import asyncio
import json
import logging
import os
import shutil
import subprocess

from .omnichannel import ChannelAdapter

logger = logging.getLogger("vivify.omnichannel.wacli")

def _find_wacli() -> str:
    w = shutil.which("wacli")
    if w:
        return w
    candidates = [
        os.path.expanduser("~/go/bin/wacli"),
        "/usr/local/bin/wacli",
        "/usr/bin/wacli",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return "wacli"

WACLI_BIN = _find_wacli()

def _run_sync(*args: str, timeout: int = 30) -> dict:
    cmd = [WACLI_BIN, "--json", *args]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            return {"ok": False, "error": r.stderr.strip() or f"exit {r.returncode}"}
        if not r.stdout.strip():
            return {"ok": True, "data": None}
        return {"ok": True, "data": json.loads(r.stdout)}
    except FileNotFoundError:
        return {"ok": False, "error": f"wacli not found ({WACLI_BIN})"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout"}
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"invalid JSON: {e}"}

class WacliWhatsAppAdapter(ChannelAdapter):
    async def push_product(self, product: dict, config: dict) -> dict:
        target_phone = config.get("target_phone", "")
        if not target_phone:
            return {"success": False, "error": "Missing target_phone in channel config"}

        name = product.get("name", "Joia")
        price = product.get("price", "")
        metal = product.get("metal", "")
        sku = product.get("sku", "")
        desc = product.get("description", "") or name

        msg = f"*{name}*"
        if metal:
            msg += f" ({metal})"
        msg += f"\n{desc}"
        if price:
            msg += f"\n💰 R$ {float(price):.2f}"
        if sku:
            msg += f"\nSKU: {sku}"

        def _send():
            return _run_sync("send", "text", "--to", target_phone, "--message", msg[:4096])

        result = await asyncio.to_thread(_send)
        if result.get("ok"):
            msg_id = ""
            if result.get("data") and isinstance(result["data"], dict):
                msg_id = result["data"].get("id", "")
            return {
                "success": True,
                "status": "synced",
                "external_id": msg_id,
                "message": "WhatsApp message sent via wacli",
            }
        return {
            "success": False,
            "status": "error",
            "message": result.get("error", "wacli send failed"),
        }

    async def delete_product(self, external_id: str, config: dict) -> dict:
        return {"success": True, "status": "deleted", "message": "WhatsApp messages cannot be deleted via wacli"}

    async def health_check(self, config: dict) -> bool:
        def _check():
            return _run_sync("doctor")
        result = await asyncio.to_thread(_check)
        if not result.get("ok"):
            return False
        data = result.get("data", {})
        if isinstance(data, dict):
            inner = data.get("data", data)
            authenticated = inner.get("authenticated", False) if isinstance(inner, dict) else False
            return bool(authenticated)
        return False
