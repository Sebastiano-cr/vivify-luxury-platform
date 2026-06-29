from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from ..services.simulator import (
    get_simulation_config,
    call_materialview_simulate,
    render_local_preview,
    MATERIAL_PRESETS,
    GEMSTONE_COLORS,
)
from ..services.wavespeed import is_available as wavespeed_available, text_to_3d, image_to_3d
from ..config import WAVESPEED_API_KEY

router = APIRouter(prefix="/simulate", tags=["simulate"])


@router.get("/materials")
def list_materials():
    return {
        "materials": {k: {"label": v["label"], "color": v["color"], "reflectivity": v["reflectivity"]} for k, v in MATERIAL_PRESETS.items()},
        "gemstones": GEMSTONE_COLORS,
    }


@router.get("/config")
def simulation_config(
    metal: str = Query("ouro_18k"),
    gemstones: str = Query(""),
    brightness: float = Query(1.0, ge=0, le=3),
    saturation: float = Query(1.0, ge=0, le=3),
    contrast: float = Query(1.0, ge=0, le=3),
    warmth: float = Query(0.5, ge=0, le=1),
    reflection: float = Query(0.5, ge=0, le=1),
    blur: float = Query(0, ge=0, le=10),
):
    gem_list = [g.strip() for g in gemstones.split(",") if g.strip()]
    lume = {
        "brightness": brightness,
        "saturation": saturation,
        "contrast": contrast,
        "warmth": warmth,
        "reflection": reflection,
        "blur": blur,
    }
    return get_simulation_config(metal, gem_list, lume)


from pydantic import BaseModel


class MaterialViewRequest(BaseModel):
    image_data: str


@router.post("/materialview")
async def proxy_materialview(
    body: MaterialViewRequest,
    metal: str = Query("ouro_18k"),
    sync: bool = Query(True),
):
    result = await call_materialview_simulate(body.image_data, metal, sync=sync)
    if result.get("error") and result.get("fallback"):
        return result
    return result


@router.get("/preview")
def local_preview(
    metal: str = Query("ouro_18k"),
    gemstones: str = Query(""),
    width: int = Query(400, ge=100, le=1024),
    height: int = Query(400, ge=100, le=1024),
):
    gem_list = [g.strip() for g in gemstones.split(",") if g.strip()]
    return render_local_preview(metal, gem_list, width, height)


@router.get("/wavespeed/status")
def wavespeed_status():
    return {
        "available": wavespeed_available(),
        "api_key_configured": bool(WAVESPEED_API_KEY),
    }


class WavespeedText3DRequest(BaseModel):
    prompt: str
    art_style: str = "realistic"
    topology: str = "triangle"
    target_polycount: int = 30000
    enable_pbr: bool = True
    output_format: str = "glb"


@router.post("/wavespeed/text-to-3d")
async def wavespeed_text_to_3d(body: WavespeedText3DRequest):
    if not wavespeed_available():
        raise HTTPException(status_code=400, detail="WAVESPEED_API_KEY not configured")
    result = await text_to_3d(
        prompt=body.prompt,
        art_style=body.art_style,
        topology=body.topology,
        target_polycount=body.target_polycount,
        enable_pbr=body.enable_pbr,
        output_format=body.output_format,
    )
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error", "Wavespeed error"))
    return result


class WavespeedImage3DRequest(BaseModel):
    image_url: Optional[str] = None
    image_base64: Optional[str] = None
    geometry_format: str = "glb"
    quality: str = "20K Triangle"
    enable_pbr: bool = True
    preview_render: bool = True


@router.post("/wavespeed/image-to-3d")
async def wavespeed_image_to_3d(body: WavespeedImage3DRequest):
    if not wavespeed_available():
        raise HTTPException(status_code=400, detail="WAVESPEED_API_KEY not configured")
    result = await image_to_3d(
        image_url=body.image_url,
        image_base64=body.image_base64,
        geometry_format=body.geometry_format,
        quality=body.quality,
        enable_pbr=body.enable_pbr,
        preview_render=body.preview_render,
    )
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error", "Wavespeed error"))
    return result
