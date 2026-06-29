from fastapi import APIRouter, Query, Request
from typing import Optional

from ..services.defense import (
    detect_scraper,
    generate_poison,
    generate_poison_cloudflare,
    log_event,
    get_stats,
)

router = APIRouter(prefix="/defense", tags=["defense"])


@router.get("/check")
async def check_request(
    request: Request,
    remote_ip: str = Query(""),
    user_agent: str = Query(""),
    path: str = Query(""),
    method: str = Query("GET"),
    rate: int = Query(0),
):
    ip = remote_ip or request.client.host if request.client else "unknown"
    ua = user_agent or request.headers.get("user-agent", "")
    p = path or request.url.path
    m = method or request.method

    result = detect_scraper(ip, ua, p, m, rate)

    if result["is_scraper"]:
        poison = generate_poison(lang="zh")
        log_event(ip, ua, p, m, result["score"], "; ".join(result["reasons"]), "poisoned", len(poison))
        return {
            "detected": True,
            "score": result["score"],
            "reasons": result["reasons"],
            "poison": poison,
        }
    else:
        log_event(ip, ua, p, m, result["score"], "; ".join(result["reasons"]), "allowed")
        return {
            "detected": False,
            "score": result["score"],
            "reasons": result["reasons"],
        }


@router.get("/poison")
async def get_poison(lang: str = Query("zh")):
    text = generate_poison(lang=lang)
    cloudflare = await generate_poison_cloudflare()
    return {
        "local_fallback": text,
        "cloudflare": cloudflare,
        "cloudflare_available": cloudflare is not None,
    }


@router.get("/stats")
def stats():
    return get_stats()
