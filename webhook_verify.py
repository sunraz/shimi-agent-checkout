#!/usr/bin/env python3
"""Verify a PayPal webhook signature (PayPal Notifications API) and extract the paid plan.
A real Mini-Shimi sale: buyer pays -> PayPal sends PAYMENT.CAPTURE.COMPLETED -> the agent
verifies the signature with PayPal itself, then activates the install. Stdlib only."""
import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import agent

def verify_signature(headers, body, webhook_id):
    tok = agent.get_token()
    payload = {"auth_algo": headers["PAYPAL-AUTH-ALGO"], "cert_url": headers["PAYPAL-CERT-URL"],
               "transmission_id": headers["PAYPAL-TRANSMISSION-ID"], "transmission_sig": headers["PAYPAL-TRANSMISSION-SIG"],
               "transmission_time": headers["PAYPAL-TRANSMISSION-TIME"], "webhook_id": webhook_id, "webhook_event": json.loads(body)}
    _, j = agent._req("POST", "/v1/notifications/verify-webhook-signature", body=payload, token=tok)
    return j.get("verification_status") == "SUCCESS"

def plan_from_event(event):
    """Pure function: only trust a COMPLETED capture; read plan/buyer from custom_id."""
    if event.get("event_type") != "PAYMENT.CAPTURE.COMPLETED": return None
    r = event["resource"]
    if r.get("status") != "COMPLETED": return None
    plan, _, buyer = (r.get("custom_id") or "").partition("|")
    if plan not in agent.PLANS: return None
    expect = agent.PLANS[plan][0]
    if r["amount"]["value"] != expect or r["amount"]["currency_code"] != "ILS": return None  # wrong amount
    return {"plan": plan, "buyer": buyer, "capture_id": r["id"]}

def selftest():
    ok = {"event_type": "PAYMENT.CAPTURE.COMPLETED", "resource": {"id": "C9", "status": "COMPLETED", "custom_id": "MINI|Dana", "amount": {"value": "299.00", "currency_code": "ILS"}}}
    assert plan_from_event(ok) == {"plan": "MINI", "buyer": "Dana", "capture_id": "C9"}
    bad = json.loads(json.dumps(ok)); bad["resource"]["amount"]["value"] = "1.00"; assert plan_from_event(bad) is None
    pend = json.loads(json.dumps(ok)); pend["resource"]["status"] = "PENDING"; assert plan_from_event(pend) is None
    other = json.loads(json.dumps(ok)); other["event_type"] = "CHECKOUT.ORDER.APPROVED"; assert plan_from_event(other) is None
    unk = json.loads(json.dumps(ok)); unk["resource"]["custom_id"] = "ZZ|x"; assert plan_from_event(unk) is None
    print("webhook selftest OK: 5 checks (valid, wrong amount, pending, wrong event, unknown plan)")

if __name__ == "__main__": selftest()
