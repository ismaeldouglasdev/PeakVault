#!/usr/bin/env python3
# scripts/stripe_setup.py
# Creates the PeakVault Stripe catalog in TEST mode: the "PeakVault Pro"
# product with a monthly subscription price (-> pro) and a one-time payment
# price (-> lifetime). Idempotent: existing entries are matched by metadata
# and reused instead of duplicated.
#
# Usage:
#   STRIPE_SECRET_KEY=sk_test_... python3 scripts/stripe_setup.py
#
# Prints KEY=VALUE lines for the price ids (append them to .env).

import os
import sys

import stripe

APP_META = {"app": "peakvault-saas"}
PRODUCT_NAME = "PeakVault Pro"
# BRL amounts (minor units). Plan F1: Pro R$15-25/mes, Lifetime R$290.
PRICES = {
    "monthly": {"kind": "monthly", "unit_amount": 1990, "recurring": {"interval": "month"}},
    "lifetime": {"kind": "lifetime", "unit_amount": 29000, "recurring": None},
}


def _paginated(cls):
    """Yield every object of a Stripe listable resource."""
    has_more, start = True, None
    while has_more:
        batch = cls.list(limit=100, starting_after=start)
        yield from batch.data
        has_more = batch.has_more
        if batch.data:
            start = batch.data[-1].id


def _find_product():
    for p in _paginated(stripe.Product):
        if p.name == PRODUCT_NAME:
            return p
    return None


def _match_price(spec):
    """Predicate over a Price object matching `spec` (amount/currency/interval)."""

    def match(p) -> bool:
        if p.unit_amount != spec["unit_amount"] or p.currency != "brl" or not p.active:
            return False
        interval = getattr(p.recurring, "interval", None)
        if spec["recurring"]:
            return interval == "month"
        return interval is None

    return match


def main() -> int:
    key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not key:
        print("STRIPE_SECRET_KEY env var required", file=sys.stderr)
        return 1
    stripe.api_key = key

    product = _find_product()
    if product is None:
        product = stripe.Product.create(name=PRODUCT_NAME, metadata=dict(APP_META, kind="product"))
        print(f"product created: {product.id}", file=sys.stderr)
    else:
        print(f"product reused:  {product.id}", file=sys.stderr)

    for key_name, spec in PRICES.items():
        existing = next((p for p in _paginated(stripe.Price) if _match_price(spec)(p)), None)
        if existing is not None:
            print(f"price reused:    {existing.id} ({key_name})", file=sys.stderr)
            print(f"STRIPE_PRICE_{key_name.upper()}={existing.id}")
            continue
        kwargs = {
            "product": product.id,
            "unit_amount": spec["unit_amount"],
            "currency": "brl",
            "metadata": dict(APP_META, kind=spec["kind"], name=key_name),
        }
        if spec["recurring"]:
            kwargs["recurring"] = spec["recurring"]
        price = stripe.Price.create(**kwargs)
        print(f"price created:   {price.id} ({key_name})", file=sys.stderr)
        print(f"STRIPE_PRICE_{key_name.upper()}={price.id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())