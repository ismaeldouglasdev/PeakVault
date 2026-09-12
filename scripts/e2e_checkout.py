#!/usr/bin/env python3
# scripts/e2e_checkout.py
# F0.4-QA: creates a fresh test user and a REAL (test-mode) Stripe Checkout
# session through the app's own billing layer, printing the hosted URL.
# The hosted page is then paid in the browser (test card 4242...) and the
# resulting webhook is verified against the local server + DB.
#
# Usage (from the repo root):
#   set -a; source .env; set +a
#   python3 scripts/e2e_checkout.py [subscription|lifetime] [email]

import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import auth, billing  # noqa: E402

MODE = sys.argv[1] if len(sys.argv) > 1 else "subscription"
EMAIL = sys.argv[2] if len(sys.argv) > 2 else f"e2e-{int(time.time())}@peakvault.test"


async def main() -> None:
    user, _ = await auth.register(EMAIL, "Test-Stripe-123!")
    url = await billing.create_checkout_session(user.id, mode=MODE)
    print(f"EMAIL={user.email}")
    print(f"USER_ID={user.id}")
    print(f"PLAN_BEFORE={user.plan}")
    print(f"CHECKOUT_URL={url}")


if __name__ == "__main__":
    asyncio.run(main())