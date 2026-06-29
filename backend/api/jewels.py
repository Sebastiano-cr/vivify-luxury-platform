from fastapi import APIRouter, HTTPException, status, Query
from datetime import datetime, timezone
import json
from uuid import uuid4
from typing import List, Optional

from ..storage.db import fetchone, fetchall, execute
from ..storage.hashchain import append_jewel_entry, get_jewel_chain
from ..models.jewel import JewelCreate, JewelUpdate, JewelOut, ProvenanceStep
from ..models.enums import MetalType, GemType, JewelStatus
from ..services.llm import SOCLLMService
from ..services.event_bus import emit

router = APIRouter(prefix="/jewels", tags=["jewels"])


def _row_to_jewel(row: dict) -> JewelOut:
    provenance_rows = fetchall(
        "SELECT step_name, description, timestamp, document_hash FROM provenance_steps WHERE jewel_id = ? ORDER BY timestamp",
        (row["id"],),
    )
    provenance = [
        ProvenanceStep(
            step_name=p["step_name"],
            description=p["description"],
            timestamp=datetime.fromisoformat(p["timestamp"]),
            document_hash=p.get("document_hash"),
        )
        for p in provenance_rows
    ]
    return JewelOut(
        id=row["id"],
        name=row["name"],
        metal=MetalType(row["metal"]),
        gemstones=[GemType(g) for g in json.loads(row["gemstones"])] if row.get("gemstones") else [],
        weight_grams=row["weight_grams"],
        origin=row.get("origin"),
        status=JewelStatus(row["status"]),
        description=row.get("description"),
        hash_chain_entry_hash=row["hash_chain_entry_hash"],
        qr_code_url=row["qr_code_url"],
        certificate_worm_key=row.get("certificate_worm_key"),
        price=row.get("price"),
        image_url=row.get("image_url"),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        provenance=provenance,
    )


@router.post("/", response_model=JewelOut, status_code=status.HTTP_201_CREATED)
async def create_jewel(jewel: JewelCreate):
    jewel_id = str(uuid4())
    metadata = jewel.model_dump(mode="json")
    metadata["action"] = "cadastro"
    metadata["jewel_id"] = jewel_id

    entry_hash = append_jewel_entry(
        event_type="vivify.jewel.created",
        jewel_id=jewel_id,
        metadata=metadata,
    )

    now = datetime.now(timezone.utc).isoformat()
    qr_code_url = f"/vivify/verify/{jewel_id}"

    execute(
        """INSERT INTO jewels (id, name, metal, gemstones, weight_grams, origin, status,
           hash_chain_entry_hash, qr_code_url, description, price, image_url, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            jewel_id,
            jewel.name,
            jewel.metal.value,
            json.dumps([g.value for g in jewel.gemstones]),
            jewel.weight_grams,
            jewel.origin,
            jewel.status.value,
            entry_hash,
            qr_code_url,
            jewel.description,
            jewel.price,
            jewel.image_url,
            now,
            now,
        ),
    )

    row = fetchone("SELECT * FROM jewels WHERE id = ?", (jewel_id,))
    result = _row_to_jewel(row)
    await emit("jewel.created", product_id=jewel_id)
    return result


@router.get("/", response_model=List[JewelOut])
def list_jewels(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    metal: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
):
    where = []
    params = []
    if metal:
        where.append("metal = ?")
        params.append(metal)
    if status:
        where.append("status = ?")
        params.append(status)
    if search:
        where.append("name LIKE ?")
        params.append(f"%{search}%")

    clause = ("WHERE " + " AND ".join(where)) if where else ""
    rows = fetchall(
        f"SELECT * FROM jewels {clause} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        tuple(params) + (limit, skip),
    )
    return [_row_to_jewel(r) for r in rows]


@router.get("/{jewel_id}", response_model=JewelOut)
def get_jewel(jewel_id: str):
    row = fetchone("SELECT * FROM jewels WHERE id = ?", (jewel_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Jewel not found")
    return _row_to_jewel(row)


@router.get("/{jewel_id}/chain", response_model=dict)
def get_jewel_chain_endpoint(jewel_id: str):
    row = fetchone("SELECT * FROM jewels WHERE id = ?", (jewel_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Jewel not found")
    entries = get_jewel_chain(jewel_id)
    return {"jewel_id": jewel_id, "entries": entries, "total": len(entries)}


@router.put("/{jewel_id}", response_model=JewelOut)
async def update_jewel(jewel_id: str, update: JewelUpdate):
    existing = fetchone("SELECT * FROM jewels WHERE id = ?", (jewel_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Jewel not found")

    updates = {}
    for field, value in update.model_dump(exclude_unset=True).items():
        if value is not None:
            if field == "gemstones":
                updates[field] = json.dumps([g.value for g in value])
            elif field in ("metal", "status"):
                updates[field] = value.value
            else:
                updates[field] = value

        if updates:
            now = datetime.now(timezone.utc).isoformat()
            updates["updated_at"] = now
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            params = list(updates.values()) + [jewel_id]
            execute(f"UPDATE jewels SET {set_clause} WHERE id = ?", tuple(params))

            meta = update.model_dump(exclude_unset=True, mode="json")
            meta["action"] = "atualizacao"
            meta["jewel_id"] = jewel_id
            append_jewel_entry(
                event_type="vivify.jewel.updated",
                jewel_id=jewel_id,
                metadata=meta,
            )

    row = fetchone("SELECT * FROM jewels WHERE id = ?", (jewel_id,))
    result = _row_to_jewel(row)
    await emit("jewel.updated", product_id=jewel_id)
    if update.status and update.status.value == "vendida":
        await emit("jewel.sold", jewel_id=jewel_id, channel="marketplace", tax=0.0)
    return result


@router.delete("/{jewel_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_jewel(jewel_id: str):
    existing = fetchone("SELECT * FROM jewels WHERE id = ?", (jewel_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Jewel not found")
    now = datetime.now(timezone.utc).isoformat()
    execute(
        "UPDATE jewels SET status = ?, updated_at = ? WHERE id = ?",
        (JewelStatus.BAIXADA.value, now, jewel_id),
    )
    append_jewel_entry(
        event_type="vivify.jewel.deleted",
        jewel_id=jewel_id,
        metadata={"action": "baixada", "jewel_id": jewel_id},
    )


_llm = SOCLLMService()


@router.post("/{jewel_id}/describe")
async def describe_jewel(jewel_id: str):
    row = fetchone("SELECT * FROM jewels WHERE id = ?", (jewel_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Jewel not found")
    description = await _llm.describe_jewel(
        name=row["name"],
        metal=row["metal"],
        gemstones=[g.value for g in [GemType(g) for g in json.loads(row["gemstones"])]] if row.get("gemstones") else [],
        weight=row["weight_grams"],
    )
    execute("UPDATE jewels SET description = ?, updated_at = ? WHERE id = ?",
            (description, datetime.now(timezone.utc).isoformat(), jewel_id))
    append_jewel_entry(
        event_type="vivify.jewel.described",
        jewel_id=jewel_id,
        metadata={"action": "descricao_gerada", "description": description},
    )
    row = fetchone("SELECT * FROM jewels WHERE id = ?", (jewel_id,))
    return _row_to_jewel(row)
