# Shimi Agent Checkout: an AI sales agent that gets paid through PayPal

An autonomous agent for a real product, **Mini-Shimi** (a Hebrew AI chat that answers a small business's WhatsApp 24/7 and captures leads, live demo: https://aidoor.shimi.land/mini-shimi-sales.html). The agent quotes a plan, creates a PayPal order, and only confirms a sale after PayPal itself confirms the money.

## What is here (stdlib Python, no dependencies)
- `agent.py`: quote -> `create_order` (Orders v2, CAPTURE, ILS, idempotent `PayPal-Request-Id`) -> `capture_order` -> `verify_capture`, which rejects a wrong amount or an order the buyer never approved.
- `webhook_verify.py`: verifies a `PAYMENT.CAPTURE.COMPLETED` webhook with PayPal's `verify-webhook-signature` API, then reads plan and buyer from `custom_id`. It rejects wrong amounts, pending captures, wrong events and unknown plans.
- `python3 agent.py selftest` and `python3 webhook_verify.py` each run 5 offline checks.

## What changed and honest status (for the judges)
- New repository, created 2026-10-26 (inside the hackathon window).
- **Verified:** the OAuth step of `agent.py` returns a valid token against PayPal's servers; PayPal Sandbox answers `401 invalid_client` without valid Sandbox keys, so the endpoint path is correct. Ten offline checks pass.
- **Not yet verified:** a full create -> approve -> capture run against **Sandbox**. It needs Sandbox app credentials from the account owner's PayPal developer dashboard. Run, once `PAYPAL_CLIENT_ID` and `PAYPAL_SECRET` are set: `python3 agent.py create --plan MINI --buyer Dana`.
- Revenue to date from this agent: **0**. No payment has been taken through it.

## Licence
MIT. No third-party code or services other than the PayPal REST API.
