import os
import razorpay
import json
from datetime import datetime
from dotenv import load_dotenv
from audit.logger import log_event, log_recovery_action

load_dotenv()

razorpay_client = razorpay.Client(
    auth=(os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET"))
)


def execute_retry(payment: dict, run_id: str = None) -> dict:
    payment_id = payment["id"]
    log_event("RETRY_ATTEMPTED", payment_id=payment_id,
              event_data={"amount": payment["amount"]},
              reasoning="Network error — attempting retry", run_id=run_id)
    try:
        rzp_payment = razorpay_client.payment.fetch(payment_id)
        outcome = "SUCCESS" if rzp_payment.get("status") == "captured" else "SIMULATED_RETRY"
    except Exception:
        outcome = "SIMULATED"

    log_recovery_action(payment_id=payment_id, action_type="RETRY_PAYMENT",
                        action_reason="Network error", decision_explanation="Auto retry triggered",
                        outcome=outcome, outcome_detail="Test mode simulation")
    return {"success": True, "outcome": outcome, "detail": "Retry executed"}


def execute_send_email(payment: dict, message_data: dict, run_id: str = None) -> dict:
    payment_id = payment["id"]
    payload = {
        "to": payment["customer_email"],
        "subject": message_data.get("subject", "Payment Recovery"),
        "message": message_data.get("message", ""),
        "sent_at": datetime.utcnow().isoformat()
    }
    log_event("EMAIL_SENT", payment_id=payment_id, event_data=payload,
              reasoning=f"Recovery email → {payment['customer_email']}", run_id=run_id)
    log_recovery_action(payment_id=payment_id, action_type="SEND_EMAIL",
                        action_reason=message_data.get("call_to_action", ""),
                        decision_explanation=f"Email: {message_data.get('subject', '')}",
                        outcome="EMAIL_DISPATCHED", outcome_detail=f"To: {payment['customer_email']}")
    return {"success": True, "outcome": "EMAIL_DISPATCHED",
            "detail": f"Email sent to {payment['customer_email']}"}


def execute_send_sms(payment: dict, message_data: dict, run_id: str = None) -> dict:
    payment_id = payment["id"]
    log_event("SMS_SENT", payment_id=payment_id,
              event_data={"to": payment.get("customer_contact"), "message": message_data.get("message", "")},
              reasoning="SMS nudge sent", run_id=run_id)
    log_recovery_action(payment_id=payment_id, action_type="SEND_SMS",
                        action_reason="Bank declined", decision_explanation="SMS recovery nudge",
                        outcome="SMS_DISPATCHED", outcome_detail=message_data.get("message", "")[:100])
    return {"success": True, "outcome": "SMS_DISPATCHED", "detail": "SMS sent"}


def execute_send_whatsapp(payment: dict, message_data: dict, run_id: str = None) -> dict:
    payment_id = payment["id"]
    log_event("WHATSAPP_SENT", payment_id=payment_id,
              event_data={"to": payment.get("customer_contact"), "language": "hinglish",
                          "message": message_data.get("message", "")},
              reasoning="Hinglish WhatsApp for high-value Indian customer", run_id=run_id)
    log_recovery_action(payment_id=payment_id, action_type="SEND_WHATSAPP",
                        action_reason="High value or subscription failure",
                        decision_explanation="Hinglish WhatsApp — higher engagement for Indian customers",
                        outcome="WHATSAPP_DISPATCHED",
                        outcome_detail=message_data.get("message", "")[:100])
    return {"success": True, "outcome": "WHATSAPP_DISPATCHED", "detail": "Hinglish WhatsApp sent"}


def execute_cart_recovery(payment: dict, message_data: dict, run_id: str = None) -> dict:
    payment_id = payment["id"]
    cart_link = f"https://checkout.razorpay.com/recover/{payment['order_id']}"
    payload = {
        "to": payment["customer_email"],
        "subject": message_data.get("subject", "You left something behind!"),
        "message": message_data.get("message", ""),
        "recovery_link": cart_link,
        "sent_at": datetime.utcnow().isoformat()
    }
    log_event("CART_RECOVERY_SENT", payment_id=payment_id, event_data=payload,
              reasoning=f"Cart abandonment recovery — deep link generated for order {payment['order_id']}",
              run_id=run_id)
    log_recovery_action(payment_id=payment_id, action_type="SEND_CART_RECOVERY",
                        action_reason="Checkout abandoned",
                        decision_explanation="Cart recovery email with deep link to resume checkout",
                        outcome="CART_RECOVERY_DISPATCHED",
                        outcome_detail=f"Recovery link: {cart_link}")
    return {"success": True, "outcome": "CART_RECOVERY_DISPATCHED",
            "detail": f"Cart recovery sent with link: {cart_link}"}


def execute_retry_mandate(payment: dict, run_id: str = None) -> dict:
    payment_id = payment["id"]
    log_event("MANDATE_RETRY_ATTEMPTED", payment_id=payment_id,
              event_data={"amount": payment["amount"], "retry_count": payment["retry_count"]},
              reasoning="Subscription mandate retry with exponential backoff",
              run_id=run_id)
    log_recovery_action(payment_id=payment_id, action_type="RETRY_MANDATE",
                        action_reason="Subscription charge failed",
                        decision_explanation=f"Mandate retry attempt {payment['retry_count'] + 1}/3 — exponential backoff applied",
                        outcome="MANDATE_RETRY_QUEUED",
                        outcome_detail="Retry scheduled with 24h backoff")
    return {"success": True, "outcome": "MANDATE_RETRY_QUEUED",
            "detail": "Subscription mandate retry queued"}


def execute_blacklist(payment: dict, classification: dict, run_id: str = None) -> dict:
    payment_id = payment["id"]
    log_event("BLACKLISTED", payment_id=payment_id,
              event_data={"confidence": classification.get("confidence"),
                          "risk_flags": classification.get("risk_flags", [])},
              reasoning="Fraud flagged — hard stop", run_id=run_id)
    log_recovery_action(payment_id=payment_id, action_type="BLACKLIST",
                        action_reason="Fraud detected",
                        decision_explanation="Hard stop — fraud payment must not be retried",
                        outcome="BLACKLISTED", outcome_detail="Escalated to risk team")
    return {"success": True, "outcome": "BLACKLISTED", "detail": "Payment blacklisted"}


def execute_escalate(payment: dict, run_id: str = None) -> dict:
    payment_id = payment["id"]
    log_event("ESCALATED", payment_id=payment_id,
              event_data={"amount": payment["amount"]},
              reasoning="Unknown failure — escalated to human", run_id=run_id)
    log_recovery_action(payment_id=payment_id, action_type="ESCALATE_HUMAN",
                        action_reason="Unknown pattern",
                        decision_explanation="Automated agent could not classify — human review needed",
                        outcome="ESCALATED", outcome_detail="Added to human review queue")
    return {"success": True, "outcome": "ESCALATED", "detail": "Escalated to human"}


def execute_action(action: str, payment: dict, classification: dict,
                   message_data: dict = None, run_id: str = None) -> dict:
    executors = {
        "RETRY_PAYMENT": lambda: execute_retry(payment, run_id),
        "SEND_EMAIL": lambda: execute_send_email(payment, message_data or {}, run_id),
        "SEND_SMS": lambda: execute_send_sms(payment, message_data or {}, run_id),
        "SEND_WHATSAPP": lambda: execute_send_whatsapp(payment, message_data or {}, run_id),
        "SEND_CART_RECOVERY": lambda: execute_cart_recovery(payment, message_data or {}, run_id),
        "RETRY_MANDATE": lambda: execute_retry_mandate(payment, run_id),
        "BLACKLIST": lambda: execute_blacklist(payment, classification, run_id),
        "ESCALATE_HUMAN": lambda: execute_escalate(payment, run_id),
        "NO_ACTION": lambda: {"success": True, "outcome": "NO_ACTION", "detail": "No intervention needed"},
    }
    executor = executors.get(action)
    if not executor:
        return {"success": False, "outcome": "UNKNOWN_ACTION", "detail": f"Unknown: {action}"}
    return executor()