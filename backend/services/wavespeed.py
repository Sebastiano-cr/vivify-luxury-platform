"""Wavespeed AI integration — text-to-3D and image-to-3D via Wavespeed REST API."""
import asyncio
import base64
import json
import logging
import os
from typing import Optional

import httpx

from ..config import WAVESPEED_API_KEY

logger = logging.getLogger("vivify.wavespeed")

WAVESPEED_BASE = "https://api.wavespeed.ai/api/v3"
TEXT_TO_3D_MODEL = "wavespeed-ai/meshy6/text-to-3d"
IMAGE_TO_3D_MODEL = "hyper3d/rodin-v2.5/image-to-3d"

POLL_INTERVAL = 2.0
MAX_POLL_SECONDS = 120


def is_available() -> bool:
    return bool(WAVESPEED_API_KEY)


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {WAVESPEED_API_KEY}",
        "Content-Type": "application/json",
    }


async def _submit_task(model_path: str, payload: dict) -> Optional[str]:
    url = f"{WAVESPEED_BASE}/{model_path}"
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.post(url, json=payload, headers=_headers())
            if resp.status_code not in (200, 201):
                logger.warning("Wavespeed submit error %s: %s", resp.status_code, resp.text[:300])
                return None
            data = resp.json()
            return data.get("task_id") or data.get("id")
        except Exception as e:
            logger.warning("Wavespeed submit failed: %s", e)
            return None


async def _poll_task(task_id: str) -> Optional[dict]:
    url = f"{WAVESPEED_BASE}/tasks/{task_id}"
    deadline = asyncio.get_event_loop().time() + MAX_POLL_SECONDS
    async with httpx.AsyncClient(timeout=10) as client:
        while asyncio.get_event_loop().time() < deadline:
            try:
                resp = await client.get(url, headers=_headers())
                if resp.status_code != 200:
                    return None
                data = resp.json()
                status = data.get("status", "")
                if status == "completed":
                    return data
                if status in ("failed", "error"):
                    logger.warning("Wavespeed task %s failed: %s", task_id, data.get("error", ""))
                    return None
            except Exception as e:
                logger.warning("Wavespeed poll error: %s", e)
                return None
            await asyncio.sleep(POLL_INTERVAL)
    logger.warning("Wavespeed task %s timed out", task_id)
    return None


async def text_to_3d(
    prompt: str,
    art_style: str = "realistic",
    topology: str = "triangle",
    target_polycount: int = 30000,
    enable_pbr: bool = True,
    output_format: str = "glb",
) -> dict:
    if not is_available():
        return {"success": False, "error": "WAVESPEED_API_KEY not configured", "fallback": True}
    payload = {
        "prompt": prompt,
        "art_style": art_style,
        "topology": topology,
        "target_polycount": target_polycount,
        "enable_pbr": enable_pbr,
        "output_format": output_format,
    }
    task_id = await _submit_task(TEXT_TO_3D_MODEL, payload)
    if not task_id:
        return {"success": False, "error": "Failed to submit text-to-3d task", "fallback": True}
    result = await _poll_task(task_id)
    if not result:
        return {"success": False, "error": "Task polling failed", "fallback": True}
    outputs = result.get("outputs") or result.get("data", {}).get("outputs", [])
    return {
        "success": True,
        "task_id": task_id,
        "outputs": outputs,
        "model_url": outputs[0] if outputs else None,
        "format": output_format,
    }


async def image_to_3d(
    image_url: Optional[str] = None,
    image_base64: Optional[str] = None,
    geometry_format: str = "glb",
    quality: str = "20K Triangle",
    enable_pbr: bool = True,
    preview_render: bool = True,
) -> dict:
    if not is_available():
        return {"success": False, "error": "WAVESPEED_API_KEY not configured", "fallback": True}

    images = []
    if image_url:
        images.append(image_url)
    elif image_base64:
        images.append(f"data:image/png;base64,{image_base64}")
    else:
        return {"success": False, "error": "No image provided", "fallback": True}

    payload = {
        "images": images,
        "geometry_file_format": geometry_format,
        "quality_and_mesh": quality,
        "material": "All" if enable_pbr else "Shaded",
        "preview_render": preview_render,
    }
    task_id = await _submit_task(IMAGE_TO_3D_MODEL, payload)
    if not task_id:
        return {"success": False, "error": "Failed to submit image-to-3d task", "fallback": True}
    result = await _poll_task(task_id)
    if not result:
        return {"success": False, "error": "Task polling failed", "fallback": True}
    outputs = result.get("outputs") or result.get("data", {}).get("outputs", [])
    return {
        "success": True,
        "task_id": task_id,
        "outputs": outputs,
        "model_url": outputs[0] if outputs else None,
        "preview_url": result.get("preview_url"),
        "format": geometry_format,
    }
