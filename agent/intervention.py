import os
import json
import random
from datetime import datetime, timedelta
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def generate_recovery_message(payment: dict, classification: dict) -> dict:
    amount_rupees = payment["amount"] / 100
    intervention = classification.get("recommended_intervention", "SEND_EMAIL")
    root_cause = classification.get("root_cause", "UNKNOWN")
    scenario_type = payment.get("scenario_type", "payment_failure")

    system_prompt = """You are PaybackAI's recovery message writer for Indian merchants.
Write recovery messages that are empathetic, clear, and action-oriented.
For WhatsApp/SMS: write in Hinglish (mix of Hindi and English), keep under 160 chars.
For cart recovery: include urgency and the specific item they left behind.
For subscription: emphasize continuity and what they'll lose access to.
For Email: write subject and body (max 100 words), professional but warm.
Respond ONLY with valid JSON."""

    extra_context = ""
    if payment.get("extra_data"):
        extra_context = f"\nExtra Context: {payment['extra_data']}"

    user_prompt = f"""Generate a recovery message:

Scenario: {scenario_type.upper()}
Amount: ₹{amount_rupees:.2f}
Root Cause: {root_cause}
Intervention: {intervention}
Customer Email: {payment['customer_email']}{extra_context}

Return JSON:
{{
  "channel": "{intervention}",
  "subject": "email subject or null",
  "message": "the message",
  "tone": "empathetic|urgent|friendly",
  "call_to_action": "what to do",
  "deep_link": "payment link placeholder or null"
}}"""

    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=512,
            response_format={"type": "json_object"}
        )
        result = json.loads(response.choices[0].message.content)
        return {"success": True, "intervention": intervention, "message_data": result}

    except Exception as e:
        return {
            "success": False,
            "intervention": intervention,
            "message_data": {
                "channel": intervention,
                "subject": f"Action needed: ₹{amount_rupees:.2f} payment",
                "message": f"Aapka ₹{amount_rupees:.2f} ka payment pending hai. Please complete karein!",
                "tone": "friendly",
                "call_to_action": "Complete your payment",
                "deep_link": None
            },
            "error": str(e)
        }


def select_intervention(classification: dict, payment: dict) -> dict:
    root_cause = classification.get("root_cause")
    recovery_potential = classification.get("recovery_potential")
    amount = payment.get("amount", 0)
    retry_count = payment.get("retry_count", 0)
    scenario_type = payment.get("scenario_type", "payment_failure")
    urgency = classification.get("urgency", "within_day")

    # Fraud — always hard stop
    if root_cause == "FRAUD_SUSPECTED":
        return {
            "action": "BLACKLIST",
            "priority": "critical",
            "reason": "Fraud detected — no recovery, flagged for review"
        }

    # Checkout abandonment
    if scenario_type == "checkout_abandonment":
        return {
            "action": "SEND_CART_RECOVERY",
            "priority": "high",
            "reason": "Cart abandoned — send recovery link with item details within 1 hour"
        }

    # Subscription failures
    if scenario_type == "subscription_failure":
        if root_cause == "MANDATE_EXPIRED":
            return {
                "action": "SEND_EMAIL",
                "priority": "high",
                "reason": "Mandate expired — email customer to set up new mandate"
            }
        if retry_count < 2:
            return {
                "action": "RETRY_MANDATE",
                "priority": "high",
                "reason": f"Subscription charge failed — retry mandate (attempt {retry_count + 1}/3)"
            }
        return {
            "action": "SEND_WHATSAPP",
            "priority": "medium",
            "reason": "Multiple mandate retries failed — Hinglish WhatsApp to customer"
        }

    # Network error — immediate retry
    if root_cause == "NETWORK_ERROR" and retry_count == 0:
        return {
            "action": "RETRY_PAYMENT",
            "priority": "high",
            "reason": "Network error — transient failure, immediate retry"
        }

    # Card expired
    if root_cause == "CARD_EXPIRED":
        return {
            "action": "SEND_EMAIL",
            "priority": "medium",
            "reason": "Card expired — email to update payment method"
        }

    # High value insufficient funds → WhatsApp Hinglish
    if root_cause == "INSUFFICIENT_FUNDS":
        if amount >= 50000:
            return {
                "action": "SEND_WHATSAPP",
                "priority": "high",
                "reason": "High-value insufficient funds — Hinglish WhatsApp nudge"
            }
        return {
            "action": "SEND_EMAIL",
            "priority": "medium",
            "reason": "Insufficient funds — email nudge to retry when funds available"
        }

    if root_cause == "BANK_DECLINED":
        return {
            "action": "SEND_SMS",
            "priority": "medium",
            "reason": "Bank declined — SMS with alternate payment method suggestion"
        }

    if root_cause in ["INVALID_DETAILS", "UPI_TIMEOUT"]:
        return {
            "action": "SEND_EMAIL",
            "priority": "medium",
            "reason": "Invalid details or UPI timeout — guide customer to retry correctly"
        }

    if recovery_potential == "NONE":
        return {
            "action": "NO_ACTION",
            "priority": "low",
            "reason": "Recovery potential is none"
        }

    return {
        "action": "ESCALATE_HUMAN",
        "priority": "low",
        "reason": "Unknown failure pattern — escalate to human"
    }


def record_promise_to_pay(payment: dict, classification: dict, run_id: str = None):
    """Record a promise-to-pay when customer is likely to commit."""
    if not classification.get("promise_to_pay_likely", False):
        return

    from audit.database import get_connection
    from datetime import datetime, timedelta

    promise_due = (datetime.utcnow() + timedelta(days=1)).isoformat()

    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO promise_tracker
            (payment_id, customer_email, customer_contact, amount,
             promised_at, promise_due_date, status)
            VALUES (?, ?, ?, ?, ?, ?, 'pending')
            """,
            (
                payment["id"],
                payment.get("customer_email"),
                payment.get("customer_contact"),
                payment.get("amount"),
                datetime.utcnow().isoformat(),
                promise_due
            )
        )
        conn.execute(
            "UPDATE failed_payments SET promise_to_pay=?, promise_due_date=? WHERE id=?",
            (datetime.utcnow().isoformat(), promise_due, payment["id"])
        )
        conn.commit()
    finally:
        conn.close()