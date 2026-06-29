"""Subscription plans and tenant limits for Vivify marketplace."""
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, Optional
from uuid import uuid4

from ..storage.db import execute, fetchone, fetchall

logger = logging.getLogger("vivify.subscriptions")


@dataclass
class Plan:
    name: str
    label: str
    price_monthly: float
    price_yearly: float
    max_products: int
    max_channels: int
    max_competitors: int
    max_scans_per_day: int
    features: list[str]
    highlighted: bool = False


PLANS: dict[str, Plan] = {
    "trial": Plan(
        name="trial",
        label="Trial",
        price_monthly=0,
        price_yearly=0,
        max_products=10,
        max_channels=1,
        max_competitors=3,
        max_scans_per_day=5,
        features=["Catálogo até 10 joias", "1 canal de venda", "3 concorrentes monitorados", "5 scans/dia", "Design Analyzer básico", "Suporte comunidade"],
    ),
    "basico": Plan(
        name="basico",
        label="Básico",
        price_monthly=97,
        price_yearly=970,
        max_products=100,
        max_channels=3,
        max_competitors=10,
        max_scans_per_day=20,
        features=["Catálogo até 100 joias", "3 canais de venda", "10 concorrentes", "20 scans/dia", "Design Analyzer completo", "Hashchain + certificação", "Suporte e-mail"],
        highlighted=False,
    ),
    "pro": Plan(
        name="pro",
        label="Profissional",
        price_monthly=297,
        price_yearly=2970,
        max_products=1000,
        max_channels=10,
        max_competitors=30,
        max_scans_per_day=100,
        features=["Catálogo ilimitado", "10 canais de venda", "30 concorrentes", "100 scans/dia", "Omnichannel completo (WhatsApp + Instagram)", "MaterialView-Pro 3D", "Suporte prioritário"],
        highlighted=True,
    ),
    "enterprise": Plan(
        name="enterprise",
        label="Enterprise",
        price_monthly=0,
        price_yearly=0,
        max_products=10000,
        max_channels=999,
        max_competitors=999,
        max_scans_per_day=9999,
        features=["Tudo do Pro", "Limites personalizados", "Onboarding automágico", "API dedicada", "SOC Gateway + CAMEL", "SLA 99.9%", "Suporte dedicado 24/7", "On-premise disponível"],
        highlighted=False,
    ),
}


def get_plan(plan_name: str) -> Optional[Plan]:
    return PLANS.get(plan_name)


def get_subscription(tenant_id: str = "default") -> Optional[dict]:
    row = fetchone("SELECT * FROM subscriptions WHERE tenant_id = ?", (tenant_id,))
    if row:
        row["features"] = json.loads(row["features_json"]) if isinstance(row["features_json"], str) else {}
    return row


def create_or_update_subscription(tenant_id: str, plan: str, stripe_customer_id: str = "", stripe_subscription_id: str = "") -> dict:
    plan_def = get_plan(plan)
    if not plan_def:
        raise ValueError(f"Invalid plan: {plan}")

    existing = fetchone("SELECT id FROM subscriptions WHERE tenant_id = ?", (tenant_id,))
    now = datetime.now(timezone.utc).isoformat()
    expires = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat() if plan != "enterprise" else None

    features = {
        "design_analyzer": plan in ("basico", "pro", "enterprise"),
        "hashchain": True,
        "omnichannel_whatsapp": plan in ("pro", "enterprise"),
        "omnichannel_instagram": plan in ("pro", "enterprise"),
        "materialview_3d": plan in ("pro", "enterprise"),
        "onboarding_automagico": plan == "enterprise",
        "soc_gateway": plan == "enterprise",
        "camel_deception": plan == "enterprise",
    }

    if existing:
        execute(
            "UPDATE subscriptions SET plan=?, status='active', expires_at=?, max_products=?, max_channels=?, "
            "max_competitors=?, max_scans_per_day=?, features_json=?, "
            "stripe_customer_id=COALESCE(?,stripe_customer_id), stripe_subscription_id=COALESCE(?,stripe_subscription_id), updated_at=? "
            "WHERE tenant_id=?",
            (plan, expires, plan_def.max_products, plan_def.max_channels, plan_def.max_competitors,
             plan_def.max_scans_per_day, json.dumps(features),
             stripe_customer_id or None, stripe_subscription_id or None, now, tenant_id),
        )
    else:
        execute(
            "INSERT INTO subscriptions (id, tenant_id, plan, status, starts_at, expires_at, "
            "max_products, max_channels, max_competitors, max_scans_per_day, features_json, created_at, updated_at) "
            "VALUES (?, ?, ?, 'active', ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (str(uuid4()), tenant_id, plan, now, expires,
             plan_def.max_products, plan_def.max_channels, plan_def.max_competitors,
             plan_def.max_scans_per_day, json.dumps(features), now, now),
        )
    return get_subscription(tenant_id)


def check_limit(tenant_id: str, resource: str) -> dict:
    sub = get_subscription(tenant_id)
    if not sub:
        return {"allowed": True, "reason": "no subscription (trial defaults)"}

    limits = {
        "products": ("max_products", "products"),
        "channels": ("max_channels", "channels"),
        "competitors": ("max_competitors", "competitors"),
        "scans_per_day": ("max_scans_per_day", "scans today"),
    }

    if resource not in limits:
        return {"allowed": True}

    col, label = limits[resource]
    limit_val = sub.get(col, 0)
    if limit_val <= 0:
        return {"allowed": False, "reason": f"{label} limit exceeded (0 allowed)", "limit": limit_val}

    if resource == "products":
        current = fetchone("SELECT COUNT(*) as cnt FROM jewels WHERE status != 'baixada'", ())["cnt"]
    elif resource == "channels":
        current = fetchone("SELECT COUNT(*) as cnt FROM channels WHERE tenant_id = ?", (tenant_id,))["cnt"]
    elif resource == "competitors":
        current = fetchone("SELECT COUNT(*) as cnt FROM competitors WHERE tenant_id = ?", (tenant_id,))["cnt"]
    elif resource == "scans_per_day":
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        current = fetchone(
            "SELECT COUNT(*) as cnt FROM sync_log WHERE created_at LIKE ? AND action = 'scan'",
            (f"{today}%",),
        )["cnt"]
    else:
        current = 0

    allowed = current < limit_val
    return {
        "allowed": allowed,
        "current": current,
        "limit": limit_val,
        "plan": sub.get("plan"),
        "reason": None if allowed else f"{label} limit reached ({current}/{limit_val})",
    }


def list_plans() -> list[dict]:
    return [
        {
            "name": p.name,
            "label": p.label,
            "price_monthly": p.price_monthly,
            "price_yearly": p.price_yearly,
            "max_products": p.max_products,
            "max_channels": p.max_channels,
            "max_competitors": p.max_competitors,
            "max_scans_per_day": p.max_scans_per_day,
            "features": p.features,
            "highlighted": p.highlighted,
        }
        for p in PLANS.values()
    ]
