import json
from datetime import datetime, timezone
from typing import Optional

from ..models.enums import MetalType, GemType, JewelStatus
from ..storage.db import fetchone, fetchall
from ..storage.hashchain import get_jewel_chain, verify_chain


def generate_certificate(jewel_id: str, public_url: str = "") -> dict:
    row = fetchone("SELECT * FROM jewels WHERE id = ?", (jewel_id,))
    if not row:
        raise ValueError("Jewel not found")

    provenance = fetchall(
        "SELECT step_name, description, timestamp, document_hash "
        "FROM provenance_steps WHERE jewel_id = ? ORDER BY timestamp",
        (jewel_id,),
    )

    chain_entries = get_jewel_chain(jewel_id)
    integrity = verify_chain()

    cert = {
        "certificate_id": f"CERT-{jewel_id[:8].upper()}",
        "jewel_id": jewel_id,
        "jewel_name": row["name"],
        "metal": row["metal"],
        "gemstones": json.loads(row["gemstones"]) if row.get("gemstones") else [],
        "weight_grams": row["weight_grams"],
        "origin": row.get("origin"),
        "status": row["status"],
        "hash_chain_entry_hash": row["hash_chain_entry_hash"],
        "chain_integrity_valid": integrity.get("valid", False),
        "chain_total_entries": integrity.get("total", 0),
        "provenance_steps": [
            {
                "step": p["step_name"],
                "description": p["description"],
                "timestamp": p["timestamp"],
                "document_hash": p.get("document_hash"),
            }
            for p in provenance
        ],
        "chain_entries": [
            {
                "event_type": e.get("event_type"),
                "timestamp": e.get("timestamp"),
                "hash": e.get("current_hash"),
                "payload": e.get("payload"),
            }
            for e in chain_entries
        ],
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "verification_url": f"{public_url}/vivify/verify/{jewel_id}",
    }
    return cert


def store_certificate_worm(jewel_id: str, cert: dict) -> str:
    worm_key = f"vivify_cert_{jewel_id}_{cert['issued_at']}"
    return worm_key


def verify_jewel(jewel_id: str, public_url: str = "") -> dict:
    row = fetchone("SELECT * FROM jewels WHERE id = ?", (jewel_id,))
    if not row:
        raise ValueError("Jewel not found")

    cert = generate_certificate(jewel_id, public_url)

    is_valid = True
    issues = []

    chain_entries = cert["chain_entries"]
    if not chain_entries:
        is_valid = False
        issues.append("No entries found in provenance chain")

    if not cert["chain_integrity_valid"]:
        is_valid = False
        issues.append("Hash chain integrity check failed")

    return {
        "jewel_id": jewel_id,
        "name": row["name"],
        "description": row.get("description", ""),
        "status": row["status"],
        "registered_at": row["created_at"],
        "authentic": is_valid,
        "issues": issues,
        "certificate": cert,
    }
