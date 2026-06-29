import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..config import AUDIT_DB_PATH


def _get_conn(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = db_path or AUDIT_DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hashchain (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type  TEXT NOT NULL,
            session_id  TEXT NOT NULL,
            tenant_id   TEXT NOT NULL DEFAULT 'vivify',
            payload     TEXT NOT NULL,
            previous_hash TEXT NOT NULL DEFAULT '',
            current_hash  TEXT NOT NULL,
            timestamp   TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_hashchain_session
        ON hashchain(session_id, tenant_id)
    """)
    conn.commit()
    return conn


def _hash_entry(event_type: str, session_id: str, tenant_id: str,
                payload: dict, previous_hash: str, timestamp: str) -> str:
    data = json.dumps({
        "event_type": event_type,
        "session_id": session_id,
        "tenant_id": tenant_id,
        "payload": payload,
        "previous_hash": previous_hash,
        "timestamp": timestamp,
    }, sort_keys=True)
    return hashlib.sha256(data.encode()).hexdigest()


def append(event_type: str, payload: dict, db_path: Optional[str] = None,
           session_id: str = "", tenant_id: str = "vivify") -> str:
    conn = _get_conn(db_path)
    prev = conn.execute(
        "SELECT current_hash FROM hashchain WHERE session_id = ? AND tenant_id = ? "
        "ORDER BY id DESC LIMIT 1",
        (session_id, tenant_id),
    ).fetchone()
    previous_hash = prev["current_hash"] if prev else ""
    timestamp = datetime.now(timezone.utc).isoformat()
    current_hash = _hash_entry(event_type, session_id, tenant_id,
                                payload, previous_hash, timestamp)
    conn.execute(
        "INSERT INTO hashchain (event_type, session_id, tenant_id, payload, "
        "previous_hash, current_hash, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (event_type, session_id, tenant_id, json.dumps(payload),
         previous_hash, current_hash, timestamp),
    )
    conn.commit()
    return current_hash


def search(session_id: str = "", tenant_id: str = "vivify",
           limit: int = 100, db_path: Optional[str] = None) -> dict:
    conn = _get_conn(db_path)
    where = ["tenant_id = ?"]
    params = [tenant_id]
    if session_id:
        where.append("session_id = ?")
        params.append(session_id)
    rows = conn.execute(
        f"SELECT * FROM hashchain WHERE {' AND '.join(where)} "
        f"ORDER BY id DESC LIMIT ?",
        params + [limit],
    ).fetchall()
    entries = [{
        "event_type": r["event_type"],
        "session_id": r["session_id"],
        "tenant_id": r["tenant_id"],
        "payload": json.loads(r["payload"]),
        "previous_hash": r["previous_hash"],
        "current_hash": r["current_hash"],
        "timestamp": r["timestamp"],
    } for r in rows]
    total = conn.execute(
        f"SELECT COUNT(*) as cnt FROM hashchain WHERE {' AND '.join(where)}",
        params,
    ).fetchone()["cnt"]
    return {"entries": entries, "total": total}


def tail(session_id: str, tenant_id: str = "vivify",
         db_path: Optional[str] = None) -> Optional[dict]:
    conn = _get_conn(db_path)
    row = conn.execute(
        "SELECT * FROM hashchain WHERE session_id = ? AND tenant_id = ? "
        "ORDER BY id DESC LIMIT 1",
        (session_id, tenant_id),
    ).fetchone()
    if not row:
        return None
    return {
        "event_type": row["event_type"],
        "session_id": row["session_id"],
        "current_hash": row["current_hash"],
        "timestamp": row["timestamp"],
    }


def verify_chain(db_path: Optional[str] = None) -> dict:
    conn = _get_conn(db_path)
    rows = conn.execute(
        "SELECT * FROM hashchain ORDER BY id ASC"
    ).fetchall()
    if not rows:
        return {"valid": True, "total": 0}
    # verify each independent chain (grouped by session_id + tenant_id)
    chains: dict[str, list] = {}
    for row in rows:
        key = f"{row['session_id']}|{row['tenant_id']}"
        chains.setdefault(key, []).append(row)
    for key, chain_rows in chains.items():
        for i, row in enumerate(chain_rows):
            expected = _hash_entry(
                row["event_type"], row["session_id"], row["tenant_id"],
                json.loads(row["payload"]),
                "" if i == 0 else chain_rows[i - 1]["current_hash"],
                row["timestamp"],
            )
            if expected != row["current_hash"]:
                return {"valid": False, "total": len(rows)}
    return {"valid": True, "total": len(rows)}


def append_jewel_entry(event_type: str, jewel_id: str, metadata: dict) -> str:
    return append(
        event_type=event_type,
        payload=metadata,
        session_id=jewel_id,
        tenant_id="vivify",
    )


def get_jewel_chain(jewel_id: str, limit: int = 100) -> list:
    result = search(session_id=jewel_id, tenant_id="vivify", limit=limit)
    return result.get("entries", [])


def get_chain_stats() -> dict:
    result = search(tenant_id="vivify", limit=0)
    integrity = verify_chain()
    return {
        "total": result.get("total", 0),
        "valid": integrity.get("valid", False),
    }
