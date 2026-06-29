"""Simulation service — material preview + Lume controls + proxy to MaterialView-Pro."""

import base64
import io
import json
import logging
import os
from typing import Optional
from urllib.parse import urljoin

import httpx

from ..config import MATERIALVIEW_URL, WAVESPEED_API_KEY

logger = logging.getLogger("vivify.simulator")

# ── Material presets (CSS filter parameters) ──────────────────────────

MATERIAL_PRESETS: dict[str, dict] = {
    "ouro_18k": {
        "label": "Ouro 18K",
        "css_filter": "sepia(0.6) saturate(2.5) hue-rotate(-10deg) brightness(1.1)",
        "color": "#D4A84B",
        "reflectivity": 0.8,
        "warmth": 0.9,
    },
    "ouro_24k": {
        "label": "Ouro 24K",
        "css_filter": "sepia(0.7) saturate(3.0) hue-rotate(-5deg) brightness(1.2)",
        "color": "#FFD700",
        "reflectivity": 0.85,
        "warmth": 1.0,
    },
    "prata_925": {
        "label": "Prata 925",
        "css_filter": "grayscale(1) brightness(1.3) contrast(1.1)",
        "color": "#C0C0C0",
        "reflectivity": 0.9,
        "warmth": 0.0,
    },
    "platina": {
        "label": "Platina",
        "css_filter": "grayscale(0.8) brightness(1.1) contrast(1.2) saturate(0.3)",
        "color": "#E5E4E2",
        "reflectivity": 0.85,
        "warmth": 0.1,
    },
    "rodio": {
        "label": "Ródio",
        "css_filter": "grayscale(0.9) brightness(1.4) contrast(1.3) saturate(0.2)",
        "color": "#F0F0F0",
        "reflectivity": 0.95,
        "warmth": 0.0,
    },
}

# ── Gemstone color overlays ───────────────────────────────────────────

GEMSTONE_COLORS: dict[str, str] = {
    "diamante": "#B9F2FF",
    "esmeralda": "#50C878",
    "safira": "#0F52BA",
    "rubi": "#E0115F",
    "ametista": "#9966CC",
    "topazio": "#FFC87C",
    "agua_marinha": "#7FFFD4",
    "turmalina": "#FF69B4",
    "citrino": "#E4D00A",
    "opala": "#A8C3D8",
    "perola": "#F5F5DC",
}


class LumeParams:
    brightness: float = 1.0
    saturation: float = 1.0
    contrast: float = 1.0
    warmth: float = 0.5
    reflection: float = 0.5
    blur: float = 0.0

    def to_css_filter(self, base_filter: str = "") -> str:
        filters = []
        if base_filter:
            filters.append(base_filter)
        if self.brightness != 1.0:
            filters.append(f"brightness({self.brightness})")
        if self.saturation != 1.0:
            filters.append(f"saturate({self.saturation})")
        if self.contrast != 1.0:
            filters.append(f"contrast({self.contrast})")
        if self.warmth != 0.5:
            sepia_val = max(0, min(1, (self.warmth - 0.5) * 2))
            filters.append(f"sepia({sepia_val})")
        if self.blur > 0:
            filters.append(f"blur({self.blur}px)")
        return " ".join(filters) if filters else "none"


def get_material_preset(metal: str) -> dict:
    return MATERIAL_PRESETS.get(metal, MATERIAL_PRESETS["ouro_18k"])


def get_simulation_config(metal: str, gemstones: list[str], lume: Optional[dict] = None) -> dict:
    material = get_material_preset(metal)
    lp = LumeParams()
    if lume:
        for k, v in lume.items():
            if hasattr(lp, k):
                setattr(lp, k, v)
    gemstone_colors = [GEMSTONE_COLORS.get(g, "#FFFFFF") for g in gemstones]
    css_filter = lp.to_css_filter(material["css_filter"])
    return {
        "metal": metal,
        "material": material,
        "lume": {
            "brightness": lp.brightness,
            "saturation": lp.saturation,
            "contrast": lp.contrast,
            "warmth": lp.warmth,
            "reflection": lp.reflection,
            "blur": lp.blur,
        },
        "css_filter": css_filter,
        "gemstone_colors": gemstone_colors,
        "wavespeed_available": bool(WAVESPEED_API_KEY),
        "materialview_available": _check_materialview(),
    }


def _check_materialview() -> bool:
    try:
        resp = httpx.get(urljoin(MATERIALVIEW_URL, "/health"), timeout=2)
        return resp.status_code == 200
    except Exception:
        return False


async def call_materialview_simulate(
    image_data: str,
    metal: str,
    lume: Optional[dict] = None,
    sync: bool = True,
) -> dict:
    """Proxy para o MaterialView-Pro."""
    material = get_material_preset(metal)
    headers = {
        "Content-Type": "application/json",
        "X-Sync-Mode": "true" if sync else "false",
    }
    payload = {
        "image": image_data,
        "material": {
            "name": material["label"],
            "category": "metal",
            "color": material["color"],
        },
        "params": lume or {},
    }
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                urljoin(MATERIALVIEW_URL, "/v1/simulate"),
                json=payload,
                headers=headers,
            )
            if resp.status_code in (200, 202):
                return resp.json()
            return {"error": f"MaterialView-Pro returned {resp.status_code}", "fallback": True}
    except Exception as e:
        logger.warning("MaterialView-Pro call failed: %s", e)
        return {"error": str(e), "fallback": True}


def render_local_preview(
    metal: str,
    gemstones: Optional[list[str]] = None,
    width: int = 400,
    height: int = 400,
) -> dict:
    """Generate a local 3D-style preview image using Pillow overlays."""
    from PIL import Image, ImageDraw

    material = get_material_preset(metal)
    bg_color = material["color"]
    gem_list = gemstones or []

    img = Image.new("RGBA", (width, height), (30, 30, 30, 255))
    draw = ImageDraw.Draw(img)

    cx, cy = width // 2, height // 2
    r = min(width, height) // 3

    def _hex_to_rgb(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    metal_rgb = _hex_to_rgb(bg_color)
    shine = tuple(min(255, c + 60) for c in metal_rgb)
    shadow = tuple(max(0, c - 40) for c in metal_rgb)

    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=metal_rgb + (255,))
    draw.ellipse([cx - r + 8, cy - r + 8, cx + r - 8, cy + r - 8], fill=shine + (180,))

    num_gems = len(gem_list)
    if num_gems > 0:
        import math
        for i, gem in enumerate(gem_list):
            gc = GEMSTONE_COLORS.get(gem, "#FFFFFF")
            gem_rgb = _hex_to_rgb(gc)
            angle = 2 * math.pi * i / num_gems
            gx = cx + int(r * 0.55 * math.cos(angle))
            gy = cy + int(r * 0.55 * math.sin(angle))
            gr = r // 5
            draw.ellipse([gx - gr, gy - gr, gx + gr, gy + gr], fill=gem_rgb + (220,))
            gs = tuple(min(255, c + 40) for c in gem_rgb)
            draw.ellipse([gx - gr // 2, gy - gr // 2, gx + gr // 2, gy + gr // 2], fill=gs + (180,))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()

    return {
        "image_base64": b64,
        "metal": metal,
        "gemstones": gem_list,
        "width": width,
        "height": height,
        "source": "local",
    }
