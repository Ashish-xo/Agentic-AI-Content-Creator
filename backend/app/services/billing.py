"""Billing: Stripe checkout + webhooks; plan catalog. 503s clearly until keys exist."""
from __future__ import annotations

from typing import Any

import stripe
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.tables import UserPlan

PLAN_LIMITS = {
    "free": {"chat_per_day": 20, "generate_per_day": 5},
    "starter": {"chat_per_day": 200, "generate_per_day": 50},
    "pro": {"chat_per_day": 1000, "generate_per_day": 300},
    "studio": {"chat_per_day": 5000, "generate_per_day": 2000},
}

PLANS = [
    {"id": "free", "name": "Free", "price_usd": 0, "limits": PLAN_LIMITS["free"]},
    {"id": "starter", "name": "Starter", "price_usd": 19, "limits": PLAN_LIMITS["starter"]},
    {"id": "pro", "name": "Pro", "price_usd": 49, "limits": PLAN_LIMITS["pro"]},
    {"id": "studio", "name": "Studio", "price_usd": 149, "limits": PLAN_LIMITS["studio"]},
]

_PRICE_IDS = {"starter": "starter", "pro": "pro", "studio": "studio"}


def _client() -> Any:
    s = get_settings()
    if not s.stripe_secret_key:
        raise HTTPException(503, "Billing not configured — set STRIPE_SECRET_KEY")
    return stripe.StripeClient(s.stripe_secret_key)


def get_plan(db: Session, user_id: str) -> str:
    row = db.query(UserPlan).filter(UserPlan.user_id == user_id).first()
    return row.plan if row else "free"


def ensure_plan_row(db: Session, user_id: str) -> UserPlan:
    row = db.query(UserPlan).filter(UserPlan.user_id == user_id).first()
    if not row:
        row = UserPlan(user_id=user_id)
        db.add(row)
        db.commit()
    return row


async def create_checkout(db: Session, user_id: str, plan_id: str) -> dict:
    if plan_id not in _PRICE_IDS:
        raise HTTPException(400, f"Unknown plan '{plan_id}'")
    client = _client()
    row = ensure_plan_row(db, user_id)
    if not row.stripe_customer_id:
        cust = client.customers.create(  # type: ignore[call-arg]
            email=f"{user_id}@content-copilot.local",
            metadata={"user_id": user_id},
        )
        row.stripe_customer_id = cust.id
        db.commit()
    # In prod, replace with pre-created Price IDs from the Stripe dashboard.
    price = client.prices.create(  # type: ignore[call-arg]
        currency="usd", unit_amount=next(p["price_usd"] for p in PLANS if p["id"] == plan_id) * 100,
        recurring={"interval": "month"},
        product_data={"name": f"Content Copilot {plan_id.title()}"},
    )
    session = client.checkout.sessions.create(  # type: ignore[call-arg]
        mode="subscription",
        customer=row.stripe_customer_id,
        line_items=[{"price": price.id, "quantity": 1}],
        success_url="http://localhost:3000/settings?upgraded=1",
        cancel_url="http://localhost:3000/settings",
        metadata={"user_id": user_id, "plan": plan_id},
        subscription_data={"metadata": {"user_id": user_id, "plan": plan_id}},
    )
    return {"checkout_url": session.url}


async def handle_webhook(db: Session, payload: bytes, sig_header: str) -> None:
    s = get_settings()
    if not s.stripe_webhook_secret:
        raise HTTPException(503, "Set STRIPE_WEBHOOK_SECRET")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, s.stripe_webhook_secret)
    except Exception:
        raise HTTPException(400, "Invalid signature")
    obj = event["data"]["object"]
    user_id = (obj.get("metadata") or obj.get("subscription_details", {}).get("metadata") or {}).get("user_id", "")
    if event["type"] in ("checkout.session.completed", "customer.subscription.updated"):
        plan = (obj.get("metadata") or {}).get("plan", "free")
        row = ensure_plan_row(db, user_id)
        row.plan = plan if plan in PLAN_LIMITS else row.plan
        db.commit()
    elif event["type"] == "customer.subscription.deleted":
        row = ensure_plan_row(db, user_id)
        row.plan = "free"
        db.commit()
