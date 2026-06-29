"""Middleware that checks subscription limits for product/channel/competitor creation."""
import json
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from ..services.subscriptions import check_limit

logger = logging.getLogger("vivify.subscription_middleware")

LIMIT_CHECKS = {
    "POST:/jewels/": "products",
    "POST:/competitors/": "competitors",
    "POST:/omnichannel/channels": "channels",
}


class SubscriptionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        key = f"{request.method}:{request.url.path}"
        if key in LIMIT_CHECKS:
            resource = LIMIT_CHECKS[key]
            tenant_id = request.query_params.get("tenant_id", "default")
            result = check_limit(tenant_id, resource)
            if not result.get("allowed"):
                return Response(
                    status_code=403,
                    content=json.dumps({
                        "error": "subscription_limit_exceeded",
                        "detail": result.get("reason", "limit reached"),
                        "limit": result.get("limit"),
                        "current": result.get("current"),
                        "plan": result.get("plan"),
                    }),
                    media_type="application/json",
                )
        return await call_next(request)
