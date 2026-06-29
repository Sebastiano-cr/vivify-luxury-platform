from fastapi import APIRouter
import httpx
from datetime import datetime, timezone

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

SERVICES = {
    "vivify":   {"url": "http://127.0.0.1:3334/health",  "label": "Vivify API"},
    "ledger":   {"url": "http://127.0.0.1:3002/accounts", "label": "Ledger"},
    "soc":      {"url": "http://127.0.0.1:3333/health",   "label": "SOC Gateway"},
    "ollama":   {"url": "http://127.0.0.1:11434/api/tags","label": "Ollama"},
    "odysseus": {"url": "http://127.0.0.1:7000/health",   "label": "Odysseus"},
}


@router.get("/health")
async def health_summary():
    results = {}
    all_up = True

    async with httpx.AsyncClient(timeout=5.0) as client:
        for key, svc in SERVICES.items():
            try:
                resp = await client.get(svc["url"])
                if resp.status_code < 500:
                    results[key] = {
                        "status": "up",
                        "code": resp.status_code,
                        "label": svc["label"],
                    }
                else:
                    results[key] = {
                        "status": "error",
                        "code": resp.status_code,
                        "label": svc["label"],
                    }
                    all_up = False
            except httpx.TimeoutException:
                results[key] = {
                    "status": "timeout",
                    "code": 0,
                    "label": svc["label"],
                }
                all_up = False
            except Exception as e:
                results[key] = {
                    "status": "down",
                    "code": 0,
                    "label": svc["label"],
                    "error": str(e),
                }
                all_up = False

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "overall": "ok" if all_up else "degraded",
        "services": results,
        "up": sum(1 for r in results.values() if r["status"] == "up"),
        "total": len(results),
    }
