import json
import logging

from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from ..storage.db import fetchone, fetchall

logger = logging.getLogger("vivify.marketplace")
router = APIRouter(prefix="/marketplace", tags=["marketplace"])


@router.get("/")
def list_products(
    search: Optional[str] = Query(None, min_length=2),
    metal: Optional[str] = Query(None),
    gemstone: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    conditions = ["status = 'disponivel'"]
    params: list = []

    if search:
        conditions.append("(name LIKE ? OR description LIKE ?)")
        term = f"%{search}%"
        params.extend([term, term])

    if metal:
        conditions.append("metal = ?")
        params.append(metal)

    if gemstone:
        conditions.append("gemstones LIKE ?")
        params.append(f'%"{gemstone}"%')

    if min_price is not None:
        conditions.append("(price IS NULL OR price >= ?)")
        params.append(min_price)

    if max_price is not None:
        conditions.append("(price IS NULL OR price <= ?)")
        params.append(max_price)

    where = " AND ".join(conditions)

    count_row = fetchone(f"SELECT COUNT(*) as cnt FROM jewels WHERE {where}", tuple(params))
    total = count_row["cnt"] if count_row else 0

    rows = fetchall(
        f"SELECT id, name, metal, gemstones, weight_grams, price, description, image_url, qr_code_url, "
        f"(SELECT COUNT(*) FROM provenance_steps WHERE jewel_id = jewels.id) as step_count "
        f"FROM jewels WHERE {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        tuple(params) + (limit, offset),
    )

    items = []
    for r in rows:
        items.append({
            "id": r["id"],
            "name": r["name"],
            "metal": r["metal"],
            "gemstones": json.loads(r["gemstones"]) if r.get("gemstones") else [],
            "weight_grams": r["weight_grams"],
            "price": r.get("price"),
            "description": r.get("description"),
            "image_url": r.get("image_url"),
            "qr_code_url": r.get("qr_code_url"),
            "step_count": r["step_count"],
        })

    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/{jewel_id}")
def get_product(jewel_id: str):
    row = fetchone(
        "SELECT id, name, metal, gemstones, weight_grams, price, description, image_url, "
        "qr_code_url, certificate_worm_key, created_at "
        "FROM jewels WHERE id = ? AND status = 'disponivel'",
        (jewel_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Joia não encontrada ou indisponível")

    provenance_steps = fetchall(
        "SELECT step_name, description, timestamp, document_hash "
        "FROM provenance_steps WHERE jewel_id = ? ORDER BY timestamp",
        (jewel_id,),
    )

    return {
        "id": row["id"],
        "name": row["name"],
        "metal": row["metal"],
        "gemstones": json.loads(row["gemstones"]) if row.get("gemstones") else [],
        "weight_grams": row["weight_grams"],
        "price": row.get("price"),
        "description": row.get("description"),
        "image_url": row.get("image_url"),
        "qr_code_url": row.get("qr_code_url"),
        "certificate_key": row.get("certificate_worm_key"),
        "created_at": row["created_at"],
        "provenance": [
            {
                "step": s["step_name"],
                "description": s["description"],
                "timestamp": s["timestamp"],
                "document_hash": s.get("document_hash"),
            }
            for s in provenance_steps
        ],
    }
