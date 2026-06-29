from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query

from ..storage.db import fetchone, fetchall, execute
from ..services.scheduler import scan_competitor, monitor_all_competitors, scheduler

router = APIRouter(prefix="/competitors", tags=["competitors"])


@router.get("/schedule")
def get_schedule():
    job = scheduler.get_job("competitor_monitoring")
    if not job:
        return {"next_run": None, "cron": "seg 08:00"}
    next_run = job.next_run_time
    return {
        "next_run": next_run.isoformat() if next_run else None,
        "cron": "seg 08:00",
    }


@router.post("/scan-all")
async def scan_all():
    await monitor_all_competitors()
    return {"scanned": True}


@router.get("/")
def list_competitors():
    rows = fetchall(
        "SELECT id, url, label, active, last_scan, last_error, created_at "
        "FROM monitored_competitors ORDER BY created_at DESC"
    )
    return {"competitors": rows, "total": len(rows)}


@router.post("/")
def add_competitor(url: str = Query(...), label: str = Query("")):
    existing = fetchone("SELECT id FROM monitored_competitors WHERE url = ?", (url,))
    if existing:
        raise HTTPException(status_code=409, detail="Competitor already monitored")
    cid = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    execute(
        "INSERT INTO monitored_competitors (id, url, label, active, created_at, updated_at) VALUES (?, ?, ?, 1, ?, ?)",
        (cid, url, label, now, now),
    )
    row = fetchone("SELECT * FROM monitored_competitors WHERE id = ?", (cid,))
    return dict(row)


@router.delete("/{competitor_id}")
def remove_competitor(competitor_id: str):
    row = fetchone("SELECT id FROM monitored_competitors WHERE id = ?", (competitor_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Competitor not found")
    execute("DELETE FROM monitored_competitors WHERE id = ?", (competitor_id,))
    return {"deleted": True, "id": competitor_id}


@router.post("/{competitor_id}/toggle")
def toggle_competitor(competitor_id: str):
    row = fetchone("SELECT id, active FROM monitored_competitors WHERE id = ?", (competitor_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Competitor not found")
    new_active = 0 if row["active"] else 1
    now = datetime.now(timezone.utc).isoformat()
    execute(
        "UPDATE monitored_competitors SET active = ?, updated_at = ? WHERE id = ?",
        (new_active, now, competitor_id),
    )
    return {"id": competitor_id, "active": bool(new_active)}


@router.post("/{competitor_id}/scan")
async def scan_now(competitor_id: str):
    row = fetchone("SELECT id, url, label FROM monitored_competitors WHERE id = ?", (competitor_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Competitor not found")
    result = await scan_competitor(row["id"], row["url"], row["label"])
    return {"id": competitor_id, "scan": result}
