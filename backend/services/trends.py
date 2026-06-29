"""Trends service — jewelry market intelligence with local storage."""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("vivify.trends")

SIGNALS_DB = Path(__file__).resolve().parent.parent / "signals_db.json"

_JEWELRY_QUERIES = {
    "design_trends": [
        "engagement ring trends",
        "custom jewelry design",
        "minimalist jewelry",
        "vintage jewelry",
        "statement necklace",
    ],
    "metal_trends": [
        "rose gold jewelry",
        "yellow gold comeback",
        "platinum vs white gold",
        "mixed metal jewelry",
    ],
    "gemstone_trends": [
        "lab grown diamond",
        "colored gemstone jewelry",
        "moissanite engagement ring",
        "sustainable gemstones",
    ],
    "market_signals": [
        "jewelry price surge",
        "gold price impact",
        "luxury jewelry market",
        "jewelry brand acquisition",
    ],
}


def _load_signals() -> list:
    if not SIGNALS_DB.exists():
        return []
    try:
        return json.loads(SIGNALS_DB.read_text())
    except (json.JSONDecodeError, OSError):
        return []


def _save_signals(signals: list):
    SIGNALS_DB.parent.mkdir(parents=True, exist_ok=True)
    SIGNALS_DB.write_text(json.dumps(signals, indent=2, default=str))


def seed_jewelry_targets() -> int:
    return len(_JEWELRY_QUERIES)


def list_targets() -> list:
    return [
        {"handle": f"vivify_{prefix}", "platform": "market",
         "queries": queries, "enabled": True}
        for prefix, queries in _JEWELRY_QUERIES.items()
    ]


def add_signal(handle: str, platform: str, text: str, topics: list[str]) -> dict:
    signals = _load_signals()
    record = {
        "target_id": f"{handle}@{platform}",
        "handle": handle,
        "platform": platform,
        "text": text,
        "topics": topics,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    signals.append(record)
    _save_signals(signals)
    return record


def query_signals(
    handle: str = "",
    platform: str = "",
    since: Optional[str] = None,
    limit: int = 50,
) -> list:
    signals = _load_signals()
    filtered = []
    for s in signals:
        if handle and s.get("handle") != handle:
            continue
        if platform and s.get("platform") != platform:
            continue
        if since and s.get("timestamp", "") < since:
            continue
        filtered.append(s)
    filtered.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
    return filtered[:limit]


def get_trends_summary() -> dict:
    signals = _load_signals()
    metals = {"ouro": 0, "prata": 0, "platina": 0, "rose_gold": 0}
    gemstones = {"diamante": 0, "esmeralda": 0, "safira": 0, "rubi": 0, "moissanite": 0}
    styles = {"minimalist": 0, "vintage": 0, "modern": 0, "custom": 0}

    for s in signals:
        text_lower = (s.get("text") or "").lower()
        for keyword in metals:
            if keyword in text_lower:
                metals[keyword] += 1
        for keyword in gemstones:
            if keyword in text_lower:
                gemstones[keyword] += 1
        for keyword in styles:
            if keyword in text_lower:
                styles[keyword] += 1

    return {
        "total_signals": len(signals),
        "total_targets": len(_JEWELRY_QUERIES),
        "metal_mentions": metals,
        "gemstone_mentions": gemstones,
        "style_mentions": styles,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }


def detect_anomalies(target_id: str = "") -> list:
    return []


def get_alerts(limit: int = 50) -> list:
    return []
