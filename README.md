# Shimi Agent Checkout: an AI agent that sells and gets paid through PayPal

An autonomous AI agent (Hebrew, WhatsApp-first) that quotes a small business, creates a PayPal order,
waits for the buyer's approval, captures the payment, and records the result. PayPal is the payment core.

## Flow
1. Agent builds a quote (plan, amount, ILS) from a chat request.
2. `create_order` -> PayPal Orders v2 (intent CAPTURE, custom_id binds plan and buyer).
3. Buyer opens the approve link (PayPal checkout).
4. `capture_order` -> PayPal captures. Agent verifies status == COMPLETED and amount matches the quote.
5. Agent writes a signed receipt (JSON) and confirms to the buyer.

## Run (Sandbox)
    export PAYPAL_CLIENT_ID=...   # Sandbox app Client ID
    export PAYPAL_SECRET=...      # Sandbox app Secret
    python3 agent.py quote --plan B --buyer "Dana"
    python3 agent.py create --plan B --buyer "Dana"     # prints approve URL
    python3 agent.py capture --order <ORDER_ID>          # after approval
    python3 agent.py selftest                            # offline logic tests, no keys needed

Defaults to the Sandbox API (https://api-m.sandbox.paypal.com). Never uses live credentials.

## Safety
- Amount is verified against the quote before the agent confirms anything.
- Secrets come from environment variables only.
- License: MIT.
