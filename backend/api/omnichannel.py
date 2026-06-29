from fastapi import APIRouter, HTTPException, Query

from ..services.omnichannel import (
    create_channel,
    update_channel,
    delete_channel,
    list_channels,
    get_channel,
    sync_product_to_channel,
    get_sync_status,
    get_sync_logs,
)

router = APIRouter(prefix="/omnichannel", tags=["omnichannel"])


@router.post("/channels")
def add_channel(
    tenant_id: str = Query("default"),
    channel_type: str = Query(..., description="whatsapp, web, instagram"),
    name: str = Query(...),
    config: str = Query("{}", description="JSON com config do canal"),
):
    import json
    try:
        config_dict = json.loads(config)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in config")
    cid = create_channel(tenant_id, channel_type, name, config_dict)
    return {"id": cid, "tenant_id": tenant_id, "type": channel_type, "name": name}


@router.get("/channels")
def list_all(tenant_id: str = Query(None)):
    return {"channels": list_channels(tenant_id)}


@router.get("/channels/{channel_id}")
def get_one(channel_id: str):
    ch = get_channel(channel_id)
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")
    return ch


@router.put("/channels/{channel_id}")
def edit_channel(
    channel_id: str,
    name: str = Query(None),
    config: str = Query(None),
    active: bool = Query(None),
):
    import json
    config_dict = json.loads(config) if config else None
    ok = update_channel(channel_id, name, config_dict, active)
    if not ok:
        raise HTTPException(status_code=404, detail="Channel not found")
    return {"updated": True, "id": channel_id}


@router.delete("/channels/{channel_id}")
def remove_channel(channel_id: str):
    ok = delete_channel(channel_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Channel not found")
    return {"deleted": True, "id": channel_id}


@router.post("/sync/{product_id}/{channel_id}")
async def sync_product(product_id: str, channel_id: str):
    result = await sync_product_to_channel(product_id, channel_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Sync failed"))
    return result


@router.get("/sync-status")
def sync_status(product_id: str = Query(None), channel_id: str = Query(None)):
    return {"syncs": get_sync_status(product_id, channel_id)}


@router.get("/logs")
def logs(channel_id: str = Query(None), limit: int = Query(50)):
    return {"logs": get_sync_logs(channel_id, limit)}
