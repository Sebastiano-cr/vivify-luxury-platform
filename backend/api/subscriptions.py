from fastapi import APIRouter, HTTPException, Query

from ..services.subscriptions import (
    get_subscription,
    create_or_update_subscription,
    check_limit,
    list_plans,
)

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.get("/plans")
def plans():
    return {"plans": list_plans()}


@router.get("/")
def subscription(tenant_id: str = Query("default")):
    sub = get_subscription(tenant_id)
    return {"subscription": sub}


@router.post("/")
def update_subscription(
    tenant_id: str = Query("default"),
    plan: str = Query(..., description="trial, basico, pro, enterprise"),
    stripe_customer_id: str = Query(""),
    stripe_subscription_id: str = Query(""),
):
    try:
        sub = create_or_update_subscription(tenant_id, plan, stripe_customer_id, stripe_subscription_id)
        return {"status": "success", "subscription": sub}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/limits")
def limits(
    tenant_id: str = Query("default"),
    resource: str = Query(..., description="products, channels, competitors, scans_per_day"),
):
    return check_limit(tenant_id, resource)
