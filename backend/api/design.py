from fastapi import APIRouter, HTTPException, Query

from ..services.design_analyzer import (
    analyze_url,
    save_theme,
    update_theme,
    delete_theme,
    list_themes,
    get_theme,
    render_preview,
    compare_themes,
)

router = APIRouter(prefix="/design", tags=["design"])


@router.post("/analyze")
async def analyze(url: str = Query(..., description="URL do site de referência")):
    try:
        result = await analyze_url(url)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-theme")
async def generate_theme(
    url: str = Query(...),
    tenant_id: str = Query("default"),
    name: str = Query("Tema Importado"),
):
    try:
        analysis = await analyze_url(url)
        theme = analysis["theme"]
        tid = save_theme(tenant_id, name, url, theme)
        return {"status": "success", "theme_id": tid, "theme": theme}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/themes")
async def themes(tenant_id: str = Query(None)):
    return {"themes": list_themes(tenant_id)}


@router.get("/themes/{theme_id}")
async def theme_detail(theme_id: str):
    th = get_theme(theme_id)
    if not th:
        raise HTTPException(status_code=404, detail="Theme not found")
    return th


@router.put("/themes/{theme_id}")
async def edit_theme(
    theme_id: str,
    name: str = Query(None),
    tokens_json: str = Query(None, description="JSON string com tokens atualizados"),
):
    import json
    tokens = json.loads(tokens_json) if tokens_json else None
    ok = update_theme(theme_id, name, tokens)
    if not ok:
        raise HTTPException(status_code=404, detail="Theme not found")
    return {"updated": True, "id": theme_id}


@router.delete("/themes/{theme_id}")
async def remove_theme(theme_id: str):
    ok = delete_theme(theme_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Theme not found")
    return {"deleted": True, "id": theme_id}


@router.get("/themes/{theme_id}/preview")
async def preview(theme_id: str):
    th = get_theme(theme_id)
    if not th:
        raise HTTPException(status_code=404, detail="Theme not found")
    html = render_preview(th)
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html)


@router.get("/compare")
async def compare(a: str = Query(..., description="ID do primeiro tema"), b: str = Query(..., description="ID do segundo tema")):
    ta = get_theme(a)
    tb = get_theme(b)
    if not ta:
        raise HTTPException(status_code=404, detail=f"Theme {a} not found")
    if not tb:
        raise HTTPException(status_code=404, detail=f"Theme {b} not found")
    return compare_themes(ta, tb)
