"""Design Analyzer — extrai DNA visual de sites referência e gera temas para o marketplace."""
import json
import logging
import os
from typing import Any, Optional

from colorthief import ColorThief
from PIL import Image
import httpx

from ..config import SOC_GATEWAY_URL
from ..storage.db import execute, fetchone, fetchall

logger = logging.getLogger("vivify.design_analyzer")


async def capture_screenshot(url: str) -> Optional[str]:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.warning("Playwright not available, cannot capture screenshot")
        return None

    os.makedirs("/tmp/vivify_design", exist_ok=True)
    path = f"/tmp/vivify_design/screenshot_{abs(hash(url))}.png"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 1024})
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)
            await page.screenshot(path=path, full_page=False)
        except Exception as e:
            logger.warning("Screenshot failed for %s: %s", url, e)
            await browser.close()
            return None
        await browser.close()
    return path


def extract_palette(image_path: str, color_count: int = 6) -> dict[str, Any]:
    try:
        ct = ColorThief(image_path)
        palette = ct.get_palette(color_count=color_count, quality=1)
        dominant = ct.get_color(quality=1)
    except Exception as e:
        logger.warning("Color extraction failed: %s", e)
        return {"error": str(e), "dominant": "#D4AF37", "palette": ["#0D0D0D", "#D4AF37", "#FFFFFF"], "is_dark": True}

    def rgb_to_hex(rgb):
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

    hex_colors = [rgb_to_hex(c) for c in palette]
    dominant_hex = rgb_to_hex(dominant)

    img = Image.open(image_path)
    pixels = list(img.getdata())
    avg_r = sum(p[0] for p in pixels) // len(pixels)
    avg_g = sum(p[1] for p in pixels) // len(pixels)
    avg_b = sum(p[2] for p in pixels) // len(pixels)
    avg_luminance = (0.299 * avg_r + 0.587 * avg_g + 0.114 * avg_b) / 255

    return {
        "dominant": dominant_hex,
        "palette": hex_colors,
        "avg_background": rgb_to_hex((avg_r, avg_g, avg_b)),
        "is_dark": avg_luminance < 0.5,
        "brightness_pct": round(avg_luminance * 100),
    }


async def describe_design(url: str, palette: dict) -> str:
    from ..services.llm import SOCLLMService
    llm = SOCLLMService()
    dom = palette.get("dominant", "#D4AF37")
    is_dark = palette.get("is_dark", True)
    colors_str = ", ".join(palette.get("palette", [])[:5])
    theme_desc = "escuro" if is_dark else "claro"
    prompt = (
        f"Com base na URL '{url}', paleta de cores [{colors_str}] "
        f"(tema {theme_desc}, cor dominante {dom}), descreva o provável "
        f"design system: estilo visual, tipografia, sensação transmitida. "
        f"Máximo 3 frases."
    )
    result = await llm.generate(prompt=prompt, temperature=0.5)
    if result.get("success"):
        return result["content"]
    return f"Tema {theme_desc} com paleta em {dom}. Design de luxo com contraste elegante."


def generate_theme(palette: dict, description: str, source_url: str) -> dict[str, Any]:
    is_dark = palette.get("is_dark", True)
    colors = palette.get("palette", ["#0D0D0D", "#D4AF37", "#FFFFFF", "#333333"])
    dominant = palette.get("dominant", "#D4AF37")

    bg = palette.get("avg_background", "#0D0D0D")
    surface = _adjust_brightness(bg, -15) if is_dark else _adjust_brightness(bg, 15)

    gold_candidates = [c for c in colors if _is_goldish(c)]
    accent = gold_candidates[0] if gold_candidates else dominant

    text_primary = "#FFFFFF" if is_dark else "#1A1A1A"
    text_secondary = "#AAAAAA" if is_dark else "#666666"

    has_serif = any(kw in description.lower() for kw in ["serifada", "serif", "classic", "elegante", "luxo"])
    has_sans = any(kw in description.lower() for kw in ["sans", "moderno", "clean", "minimalist"])

    return {
        "source_url": source_url,
        "description": description,
        "colors": {
            "primary": dominant,
            "accent": accent,
            "background": bg,
            "surface": surface,
            "text_primary": text_primary,
            "text_secondary": text_secondary,
        },
        "typography": {
            "family_headings": "'Playfair Display', serif" if has_serif else "'Inter', sans-serif",
            "family_body": "'Inter', sans-serif" if has_sans else "'Playfair Display', serif",
        },
        "is_dark": is_dark,
        "lume_default": 65 if is_dark else 40,
    }


async def analyze_url(url: str) -> dict[str, Any]:
    logger.info("Analyzing design from %s", url)
    try:
        screenshot = await capture_screenshot(url)
    except RuntimeError:
        screenshot = None

    if not screenshot:
        palette = {"dominant": "#D4AF37", "palette": ["#0D0D0D", "#D4AF37", "#FFFFFF"], "is_dark": True}
        description = "Design de luxo com fundo escuro e detalhes dourados."
    else:
        palette = extract_palette(screenshot)
        description = await describe_design(url, palette)

    theme = generate_theme(palette, description, url)

    return {
        "url": url,
        "palette": palette,
        "description": description,
        "theme": theme,
    }


def save_theme(tenant_id: str, name: str, source_url: str, theme_json: dict) -> str:
    import uuid
    tid = str(uuid.uuid4())
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    execute(
        "INSERT INTO themes (id, tenant_id, name, source_url, tokens_json, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (tid, tenant_id, name, source_url, json.dumps(theme_json), now, now),
    )
    return tid


def update_theme(theme_id: str, name: str = None, tokens_json: dict = None) -> bool:
    row = fetchone("SELECT id FROM themes WHERE id = ?", (theme_id,))
    if not row:
        return False
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    if name is not None:
        execute("UPDATE themes SET name = ?, updated_at = ? WHERE id = ?", (name, now, theme_id))
    if tokens_json is not None:
        execute("UPDATE themes SET tokens_json = ?, updated_at = ? WHERE id = ?", (json.dumps(tokens_json), now, theme_id))
    return True


def delete_theme(theme_id: str) -> bool:
    row = fetchone("SELECT id FROM themes WHERE id = ?", (theme_id,))
    if not row:
        return False
    execute("DELETE FROM themes WHERE id = ?", (theme_id,))
    return True


def list_themes(tenant_id: str = None) -> list[dict]:
    if tenant_id:
        return fetchall(
            "SELECT id, tenant_id, name, source_url, created_at FROM themes WHERE tenant_id = ? ORDER BY created_at DESC",
            (tenant_id,),
        )
    return fetchall(
        "SELECT id, tenant_id, name, source_url, created_at FROM themes ORDER BY created_at DESC"
    )


def get_theme(theme_id: str) -> Optional[dict]:
    row = fetchone(
        "SELECT id, tenant_id, name, source_url, tokens_json, created_at FROM themes WHERE id = ?",
        (theme_id,),
    )
    if row:
        row["tokens"] = json.loads(row["tokens_json"]) if isinstance(row["tokens_json"], str) else row["tokens_json"]
    return row


def render_preview(theme: dict) -> str:
    tokens = theme.get("tokens", theme)
    colors = tokens.get("colors", {})
    typography = tokens.get("typography", {})
    is_dark = tokens.get("is_dark", True)
    bg = colors.get("background", "#0D0D0D")
    surface = colors.get("surface", "#1A1A1A")
    primary = colors.get("primary", "#D4AF37")
    accent = colors.get("accent", "#D4AF37")
    text_p = colors.get("text_primary", "#FFFFFF")
    text_s = colors.get("text_secondary", "#AAAAAA")
    font_h = typography.get("family_headings", "'Playfair Display', serif")
    font_b = typography.get("family_body", "'Inter', sans-serif")

    hex_swatches = "".join(
        f'<div style="width:40px;height:40px;border-radius:8px;background:{c};border:1px solid rgba(255,255,255,0.1);flex-shrink:0;" title="{c}"></div>'
        for c in set(v for v in colors.values() if v.startswith("#"))
    )

    return f"""<div style="background:{bg};color:{text_p};padding:20px;border-radius:12px;font-family:{font_b};max-width:400px">
  <div style="display:flex;gap:6px;margin-bottom:16px;flex-wrap:wrap">{hex_swatches}</div>
  <h2 style="font-family:{font_h};color:{primary};margin:0 0 8px 0;font-size:20px;font-weight:700;">{theme.get('name','Preview')}</h2>
  <p style="color:{text_s};font-size:13px;margin:0 0 12px 0;">{tokens.get('description','')[:120]}</p>
  <div style="background:{surface};padding:12px;border-radius:8px;font-size:12px;">
    <div style="color:{accent};font-weight:600;">Tipografia</div>
    <div style="color:{text_s};margin-top:4px;">Headings: {font_h}</div>
    <div style="color:{text_s};">Body: {font_b}</div>
    <div style="color:{accent};font-weight:600;margin-top:8px;">Lume</div>
    <div style="color:{text_s};">Intensidade padrão: {tokens.get('lume_default',50)}%</div>
  </div>
</div>"""


def compare_themes(theme_a: dict, theme_b: dict) -> dict:
    ta = theme_a.get("tokens", theme_a)
    tb = theme_b.get("tokens", theme_b)
    return {
        "a": {"id": theme_a.get("id"), "name": theme_a.get("name"), "source_url": theme_a.get("source_url"), "tokens": ta},
        "b": {"id": theme_b.get("id"), "name": theme_b.get("name"), "source_url": theme_b.get("source_url"), "tokens": tb},
        "differences": {
            "is_dark": ta.get("is_dark") != tb.get("is_dark"),
            "colors": {
                "primary": {"a": ta.get("colors", {}).get("primary"), "b": tb.get("colors", {}).get("primary")},
                "accent": {"a": ta.get("colors", {}).get("accent"), "b": tb.get("colors", {}).get("accent")},
                "background": {"a": ta.get("colors", {}).get("background"), "b": tb.get("colors", {}).get("background")},
            },
            "typography": {
                "headings": {"a": ta.get("typography", {}).get("family_headings"), "b": tb.get("typography", {}).get("family_headings")},
            },
            "lume": {"a": ta.get("lume_default"), "b": tb.get("lume_default")},
        },
    }


def _adjust_brightness(hex_color: str, amount: int) -> str:
    hex_color = hex_color.lstrip("#")
    r = max(0, min(255, int(hex_color[0:2], 16) + amount))
    g = max(0, min(255, int(hex_color[2:4], 16) + amount))
    b = max(0, min(255, int(hex_color[4:6], 16) + amount))
    return f"#{r:02x}{g:02x}{b:02x}"


def _is_goldish(hex_color: str) -> bool:
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return r > 150 and g > 120 and b < 100 and r > b * 1.5
