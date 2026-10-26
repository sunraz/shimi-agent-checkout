#!/usr/bin/env python3
"""Shimi Agent Checkout: AI sales agent that gets paid through PayPal (Sandbox by default).
Stdlib only. Secrets from env: PAYPAL_CLIENT_ID, PAYPAL_SECRET. Optional PAYPAL_ENV=live (not used by demo)."""
import os, sys, json, base64, argparse, hashlib, time, urllib.request, urllib.error

API = {"sandbox": "https://api-m.sandbox.paypal.com", "live": "https://api-m.paypal.com"}
ENV = os.environ.get("PAYPAL_ENV", "sandbox")
PLANS = {  # plan -> (amount ILS, Hebrew name)
    "B": ("49.90", "Shimi plan B - basic"),
    "C": ("99.90", "Shimi plan C - pro"),
    "MINI": ("299.00", "Mini-Shimi WhatsApp chat install"),
}

class PayPalError(Exception):
    pass

def _req(method, path, body=None, token=None, basic=None, form=None, request_id=None):
    url = API[ENV] + path
    headers = {"User-Agent": "shimi-agent/1.0"}
    data = None
    if basic:
        headers["Authorization"] = "Basic " + base64.b64encode(basic.encode()).decode()
    if token:
        headers["Authorization"] = "Bearer " + token
    if form is not None:
        data = form.encode(); headers["Content-Type"] = "application/x-www-form-urlencoded"
    if body is not None:
        data = json.dumps(body).encode(); headers["Content-Type"] = "application/json"
    if request_id:
        headers["PayPal-Request-Id"] = request_id  # idempotency: safe retries, no double charge
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers, method=method), timeout=30) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        try: detail = json.loads(e.read())
        except Exception: detail = {}
        raise PayPalError(f"HTTP {e.code} {path}: {detail.get('error') or detail.get('name')} {detail.get('error_description') or detail.get('message','')}")

def get_token():
    cid, sec = os.environ.get("PAYPAL_CLIENT_ID", ""), os.environ.get("PAYPAL_SECRET", "")
    if not cid or not sec:
        raise PayPalError("missing PAYPAL_CLIENT_ID / PAYPAL_SECRET (Sandbox app credentials)")
    _, j = _req("POST", "/v1/oauth2/token", basic=f"{cid}:{sec}", form="grant_type=client_credentials")
    return j["access_token"]

def build_quote(plan, buyer):
    if plan not in PLANS: raise ValueError(f"unknown plan {plan}")
    amount, name = PLANS[plan]
    q = {"plan": plan, "item": name, "amount": amount, "currency": "ILS", "buyer": buyer}
    q["quote_id"] = hashlib.sha256(json.dumps(q, sort_keys=True).encode()).hexdigest()[:12]
    return q

def create_order(quote):
    tok = get_token()
    body = {"intent": "CAPTURE",
            "purchase_units": [{"reference_id": quote["quote_id"], "custom_id": f'{quote["plan"]}|{quote["buyer"]}',
                                "description": quote["item"],
                                "amount": {"currency_code": quote["currency"], "value": quote["amount"]}}],
            "payment_source": {"paypal": {"experience_context": {"brand_name": "Shimi", "locale": "he-IL",
                                                                 "user_action": "PAY_NOW", "shipping_preference": "NO_SHIPPING",
                                                                 "return_url": "https://example.com/return", "cancel_url": "https://example.com/cancel"}}}}
    _, j = _req("POST", "/v2/checkout/orders", body=body, token=tok, request_id="shimi-" + quote["quote_id"])
    link = next((l["href"] for l in j.get("links", []) if l["rel"] in ("payer-action", "approve")), None)
    return {"order_id": j["id"], "status": j["status"], "approve_url": link}

def verify_capture(quote, order):
    """Pure check, used before the agent confirms anything to the buyer."""
    pu = order["purchase_units"][0]
    cap = pu["payments"]["captures"][0]
    ok = (order["status"] == "COMPLETED" and cap["status"] == "COMPLETED"
          and cap["amount"]["value"] == quote["amount"] and cap["amount"]["currency_code"] == quote["currency"])
    return ok, cap

def capture_order(order_id, quote):
    tok = get_token()
    _, order = _req("POST", f"/v2/checkout/orders/{order_id}/capture", body={}, token=tok, request_id="cap-" + order_id)
    ok, cap = verify_capture(quote, order)
    receipt = {"order_id": order_id, "capture_id": cap["id"], "amount": cap["amount"], "verified": ok, "ts": int(time.time())}
    receipt["sig"] = hashlib.sha256(json.dumps(receipt, sort_keys=True).encode()).hexdigest()
    return receipt

def selftest():
    q = build_quote("B", "Dana"); assert q["amount"] == "49.90" and len(q["quote_id"]) == 12
    good = {"status": "COMPLETED", "purchase_units": [{"payments": {"captures": [{"id": "C1", "status": "COMPLETED", "amount": {"value": "49.90", "currency_code": "ILS"}}]}}]}
    assert verify_capture(q, good)[0] is True
    wrong_amt = json.loads(json.dumps(good)); wrong_amt["purchase_units"][0]["payments"]["captures"][0]["amount"]["value"] = "1.00"
    assert verify_capture(q, wrong_amt)[0] is False          # underpayment is rejected
    pending = json.loads(json.dumps(good)); pending["status"] = "PAYER_ACTION_REQUIRED"
    assert verify_capture(q, pending)[0] is False            # unapproved order is rejected
    try: build_quote("Z", "x"); assert False
    except ValueError: pass
    try: os.environ.pop("PAYPAL_CLIENT_ID", None); get_token(); assert False
    except PayPalError: pass
    print("selftest OK: 5 checks (quote, good capture, wrong amount, unapproved, missing keys)")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    for c in ("quote", "create"):
        p = sp.add_parser(c); p.add_argument("--plan", default="B"); p.add_argument("--buyer", default="buyer")
    p = sp.add_parser("capture"); p.add_argument("--order", required=True); p.add_argument("--plan", default="B"); p.add_argument("--buyer", default="buyer")
    sp.add_parser("selftest")
    a = ap.parse_args()
    if a.cmd == "selftest": selftest()
    elif a.cmd == "quote": print(json.dumps(build_quote(a.plan, a.buyer), ensure_ascii=False, indent=1))
    elif a.cmd == "create": print(json.dumps(create_order(build_quote(a.plan, a.buyer)), indent=1))
    elif a.cmd == "capture": print(json.dumps(capture_order(a.order, build_quote(a.plan, a.buyer)), indent=1))
