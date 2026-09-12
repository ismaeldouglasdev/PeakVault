# app/billing.py
# Stripe billing service: Checkout sessions, webhook handling and the
# customer portal. Price IDs and keys come from the environment so the same
# code runs in test/live modes without changes.

import os

import stripe

from app import db

# Price IDs are injected via env: STRIPE_PRICE_MONTHLY (subscription -> pro)
# and STRIPE_PRICE_LIFETIME (one-time payment -> lifetime).
_PRICE_IDS = {
    "subscription": os.getenv("STRIPE_PRICE_MONTHLY", "price_monthly"),
    "payment": os.getenv("STRIPE_PRICE_LIFETIME", "price_lifetime"),
}

# Billing mode -> target plan recorded on the user after a completed checkout.
_PLAN_BY_MODE = {
    "subscription": "pro",
    "payment": "lifetime",
}

_DEFAULT_SUCCESS_URL = "http://localhost:8501/?checkout=success"
_DEFAULT_CANCEL_URL = "http://localhost:8501/?checkout=cancelled"
_DEFAULT_PORTAL_RETURN_URL = "http://localhost:8501/"


def _api_key() -> str:
    """Stripe secret key from the environment (raises when unset)."""
    key = os.getenv("STRIPE_SECRET_KEY", "")
    if not key:
        raise RuntimeError("STRIPE_SECRET_KEY is not configured")
    return key


def _webhook_secret() -> str:
    """Stripe webhook signing secret from the environment (raises when unset)."""
    secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    if not secret:
        raise RuntimeError("STRIPE_WEBHOOK_SECRET is not configured")
    return secret


def _get_user_or_raise(user_id: int) -> db.User:
    """Fetch a user outside an active session, raising ValueError if missing."""
    with db.get_session() as session:
        user = session.get(db.User, user_id)
    if user is None:
        raise ValueError(f"user {user_id} does not exist")
    return user


async def create_checkout_session(
    user_id: int,
    mode: str = "subscription",
    success_url: str | None = None,
    cancel_url: str | None = None,
) -> str:
    """Create a Stripe Checkout session and return its hosted URL.

    The session carries ``user_id`` and the target plan in its metadata so the
    webhook can upgrade the right account on payment success. If the user
    already has a Stripe customer id, it is reused (no duplicate customers).

    Raises ValueError for unknown modes or a missing user, and RuntimeError
    when STRIPE_SECRET_KEY is not configured.
    """
    if mode not in _PLAN_BY_MODE:
        raise ValueError(f"unknown billing mode: {mode!r}")
    target_plan = _PLAN_BY_MODE[mode]
    user = _get_user_or_raise(user_id)

    stripe.api_key = _api_key()
    checkout_params = {
        "mode": mode,
        "client_reference_id": str(user_id),
        "metadata": {"user_id": str(user_id), "plan": target_plan},
        "line_items": [{"price": _PRICE_IDS[mode], "quantity": 1}],
        "success_url": success_url or _DEFAULT_SUCCESS_URL,
        "cancel_url": cancel_url or _DEFAULT_CANCEL_URL,
    }
    if user.stripe_customer_id:
        checkout_params["customer"] = user.stripe_customer_id

    checkout = stripe.checkout.Session.create(**checkout_params)
    return checkout.url


async def handle_webhook(payload: bytes, sig_header: str) -> dict:
    """Verify a Stripe webhook and apply the plan change when a checkout completes.

    Returns {"ok": True, "event": <type>} for every verified event; completed
    checkouts also include {"user_id", "plan"}. Raises
    stripe.error.SignatureVerificationError for invalid signatures (the caller
    should respond HTTP 400).
    """
    stripe.api_key = _api_key()
    event = stripe.Webhook.construct_event(payload, sig_header, _webhook_secret())

    if event["type"] != "checkout.session.completed":
        return {"ok": True, "event": event["type"]}

    checkout = event["data"]["object"]
    user_id = int(checkout["metadata"]["user_id"])
    try:
        target_plan = checkout["metadata"]["plan"]
    except KeyError:
        target_plan = "pro"

    with db.get_session() as session:
        user = session.get(db.User, user_id)
        if user is None:
            raise ValueError(f"user {user_id} does not exist")
        user.plan = target_plan
        try:
            customer_id = checkout["customer"]
        except KeyError:
            customer_id = None
        if customer_id:
            user.stripe_customer_id = customer_id
        session.commit()
        upgraded_plan = user.plan

    return {
        "ok": True,
        "event": event["type"],
        "user_id": user_id,
        "plan": upgraded_plan,
    }


async def create_portal_session(user_id: int, return_url: str | None = None) -> str:
    """Return a Stripe customer-portal URL for the given user.

    Requires the user to already have a Stripe customer id (captured by the
    webhook on the first successful checkout).

    Raises ValueError if the user or their customer id is missing, and
    RuntimeError when STRIPE_SECRET_KEY is not configured.
    """
    user = _get_user_or_raise(user_id)
    if not user.stripe_customer_id:
        raise ValueError(f"user {user_id} has no Stripe customer id")

    stripe.api_key = _api_key()
    portal = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=return_url or _DEFAULT_PORTAL_RETURN_URL,
    )
    return portal.url