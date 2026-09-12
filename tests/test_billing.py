# tests/test_billing.py
# Stripe billing tests. The Stripe SDK surface is mocked (no keys, no network).

from unittest.mock import patch

import pytest
import stripe as stripe_sdk

from app import db

db.configure_engine("sqlite:///:memory:")
db.create_all()

from app.auth import register
from app.billing import (
    create_checkout_session,
    create_portal_session,
    handle_webhook,
)
from app.storage import create_list


def _completed_event(user_id: int, plan: str = "pro", customer: str = "cus_test123") -> dict:
    """Fake Stripe ``checkout.session.completed`` payload."""
    return {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {"user_id": str(user_id), "plan": plan},
                "customer": customer,
            }
        },
    }


def _stripe_patch():
    """Replace the env-backed helpers so no real keys/secrets are needed."""
    return patch.multiple(
        "app.billing",
        _api_key=lambda: "sk_test_xxx",
        _webhook_secret=lambda: "whsec_test",
    )


def _fake_session(url: str):
    return type("FakeStripeSession", (), {"url": url})()


@pytest.mark.asyncio
async def test_create_checkout_session_returns_hosted_url():
    user, _ = await register("b-checkout@example.com", "secret123")

    with _stripe_patch(), patch(
        "stripe.checkout.Session.create",
        return_value=_fake_session("https://checkout.stripe.com/c/pay/cs_test123"),
    ) as create:
        url = await create_checkout_session(user.id)

    assert url.startswith("https://checkout.stripe.com/c/pay/")
    _, kwargs = create.call_args
    assert kwargs["mode"] == "subscription"
    assert kwargs["metadata"] == {"user_id": str(user.id), "plan": "pro"}
    assert kwargs["client_reference_id"] == str(user.id)


@pytest.mark.asyncio
async def test_create_checkout_session_reuses_customer_id():
    user, _ = await register("b-checkout-customer@example.com", "secret123")
    with db.get_session() as session:
        stored = session.get(db.User, user.id)
        stored.stripe_customer_id = "cus_existing"
        session.commit()

    with _stripe_patch(), patch(
        "stripe.checkout.Session.create",
        return_value=_fake_session("https://checkout.stripe.com/x"),
    ) as create:
        await create_checkout_session(user.id)

    _, kwargs = create.call_args
    assert kwargs["customer"] == "cus_existing"


@pytest.mark.asyncio
async def test_create_checkout_session_rejects_unknown_mode():
    user, _ = await register("b-checkout-mode@example.com", "secret123")
    with _stripe_patch(), pytest.raises(ValueError, match="unknown billing mode"):
        await create_checkout_session(user.id, mode="weird")


@pytest.mark.asyncio
async def test_handle_webhook_upgrades_free_user_to_pro():
    user, _ = await register("b-webhook@example.com", "secret123")
    assert user.plan == "free"

    with _stripe_patch(), patch(
        "stripe.Webhook.construct_event", return_value=_completed_event(user.id)
    ):
        result = await handle_webhook(b"{}", "test_sig")

    assert result["ok"] is True
    assert result["plan"] == "pro"
    with db.get_session() as session:
        stored = session.get(db.User, user.id)
        assert stored.plan == "pro"
        assert stored.stripe_customer_id == "cus_test123"


@pytest.mark.asyncio
async def test_handle_webhook_ignores_other_events():
    user, _ = await register("b-webhook-ignore@example.com", "secret123")
    event = {"type": "invoice.payment_succeeded", "data": {"object": {}}}
    with _stripe_patch(), patch("stripe.Webhook.construct_event", return_value=event):
        result = await handle_webhook(b"{}", "test_sig")
    assert result == {"ok": True, "event": "invoice.payment_succeeded"}


@pytest.mark.asyncio
async def test_handle_webhook_rejects_bad_signature():
    await register("b-webhook-badsig@example.com", "secret123")

    def raise_bad_sig(payload, sig_header, secret):
        raise stripe_sdk.error.SignatureVerificationError("bad signature", payload)

    with _stripe_patch(), patch(
        "stripe.Webhook.construct_event", side_effect=raise_bad_sig
    ):
        with pytest.raises(stripe_sdk.error.SignatureVerificationError):
            await handle_webhook(b"{}", "bad_sig")


@pytest.mark.asyncio
async def test_plan_upgrade_unlocks_list_quota():
    # A free user is capped at 1 list; after the webhook upgrade the cap lifts.
    user, _ = await register("b-quota@example.com", "secret123")

    await create_list(user.id, "Only list", [{"a": 1}])
    with pytest.raises(ValueError, match="List quota exceeded"):
        await create_list(user.id, "Second list", [{"a": 1}])

    with _stripe_patch(), patch(
        "stripe.Webhook.construct_event", return_value=_completed_event(user.id)
    ):
        await handle_webhook(b"{}", "test_sig")

    second = await create_list(user.id, "Second list", [{"a": 1}])
    assert second.name == "Second list"


@pytest.mark.asyncio
async def test_create_portal_session_requires_customer_id():
    user, _ = await register("b-portal-none@example.com", "secret123")
    with _stripe_patch(), pytest.raises(ValueError, match="no Stripe customer"):
        await create_portal_session(user.id)


@pytest.mark.asyncio
async def test_create_portal_session_returns_url():
    user, _ = await register("b-portal@example.com", "secret123")
    with db.get_session() as session:
        stored = session.get(db.User, user.id)
        stored.stripe_customer_id = "cus_test123"
        session.commit()

    with _stripe_patch(), patch(
        "stripe.billing_portal.Session.create",
        return_value=_fake_session("https://billing.stripe.com/session/cus_test123"),
    ) as portal:
        url = await create_portal_session(user.id)

    assert url.startswith("https://billing.stripe.com/")
    _, kwargs = portal.call_args
    assert kwargs["customer"] == "cus_test123"