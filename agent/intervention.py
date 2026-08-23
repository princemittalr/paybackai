import os
import json
import random
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

HINGLISH_TEMPLATES = [
    "Aapka payment fail ho gaya hai. Kya aap dobara try kar sakte hain? ₹{amount} ka payment pending hai.",
    "Hi {name}! Aapka ₹{amount} ka transaction complete nahi hua. Ek baar retry karein — sirf 2 minute lagenge!",
    "Namaste! Aapka order ready hai but payment stuck hai. ₹{amount} pay karke apna order complete karein.",
]

EMAIL_SUBJECT_TEMPLATES = [
    "Action needed: Your payment of ₹{amount} failed",
    "Complete your payment of ₹{amount} — your order is waiting",
    "Payment issue detected — let's fix it together",
]


def generate_recovery_message(payment: dict, classification: dict) -> dict:
    amount_rupees = payment["amount"] / 100
    intervention = classification.get("recommended_intervention", "SEND_EMAIL")
    root_cause = classification.get("root_cause", "UNKNOWN")

    system_prompt = """You are PaybackAI's recovery message writer for Indian merchants.
Write recovery messages that are empathetic, clear, and action-oriented.
For WhatsApp/SMS: write in Hinglish (mix of Hindi and English), keep under 160 chars.
For Email: write a short subject and body (max 100 words), professional but warm.
Respond ONLY with valid JSON. No text outside JSON."""

    user_prompt = f"""Generate a recovery message for this failed payment:

Amount: ₹{amount_rupees:.2f}
Root Cause: {root_cause}
Intervention Type: {intervention}
Customer Email: {payment['customer_email']}
Retry Count: {payment['retry_count']}

Return JSON with this exact schema:
{{
  "channel": "{intervention}",
  "subject": "email subject line or null",
  "message": "the actual message to send",
  "tone": "empathetic|urgent|friendly",
  "call_to_action": "what you want customer to do"
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
        return {
            "success": True,
            "intervention": intervention,
            "message_data": result
        }

    except Exception as e:
        amount_rupees_fmt = f"{amount_rupees:.2f}"
        fallback_message = random.choice(HINGLISH_TEMPLATES).format(
            amount=amount_rupees_fmt,
            name=payment.get("customer_email", "Customer").split(".")[0].title()
        )
        return {
            "success": False,
            "intervention": intervention,
            "message_data": {
                "channel": intervention,
                "subject": EMAIL_SUBJECT_TEMPLATES[0].format(amount=amount_rupees_fmt),
                "message": fallback_message,
                "tone": "friendly",
                "call_to_action": "Complete your payment"
            },
            "error": str(e)
        }


def select_intervention(classification: dict, payment: dict) -> dict:
    root_cause = classification.get("root_cause")
    recovery_potential = classification.get("recovery_potential")
    amount = payment.get("amount", 0)
    retry_count = payment.get("retry_count", 0)

    # Decision matrix
    if root_cause == "FRAUD_SUSPECTED":
        return {
            "action": "BLACKLIST",
            "priority": "critical",
            "reason": "Fraud detected — no recovery, flagged for review"
        }

    if root_cause == "NETWORK_ERROR" and retry_count == 0:
        return {
            "action": "RETRY_PAYMENT",
            "priority": "high",
            "reason": "Network errors are transient — immediate retry has high success rate"
        }

    if root_cause == "CARD_EXPIRED":
        return {
            "action": "SEND_EMAIL",
            "priority": "medium",
            "reason": "Card expired — customer must update payment method, email is best channel"
        }

    if root_cause == "INSUFFICIENT_FUNDS":
        if amount >= 50000:
            return {
                "action": "SEND_WHATSAPP",
                "priority": "high",
                "reason": "High value payment with insufficient funds — Hinglish WhatsApp nudge for Indian customers"
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
            "reason": "Bank declined — customer needs to contact bank or use different payment method"
        }

    if root_cause == "INVALID_DETAILS":
        return {
            "action": "SEND_EMAIL",
            "priority": "medium",
            "reason": "Invalid details entered — guide customer to re-enter correct information"
        }

    if recovery_potential == "NONE":
        return {
            "action": "NO_ACTION",
            "priority": "low",
            "reason": "Recovery potential is none — no intervention warranted"
        }

    return {
        "action": "ESCALATE_HUMAN",
        "priority": "low",
        "reason": "Unknown failure type — escalate to human agent for review"
    }


if __name__ == "__main__":
    test_payment = {
        "id": "pay_test_001",
        "amount": 99900,
        "failure_reason": "Insufficient funds",
        "failure_code": "BAD_REQUEST_ERROR",
        "customer_email": "priya.sharma@gmail.com",
        "retry_count": 0,
        "created_at": datetime.utcnow().isoformat()
    }

    test_classification = {
        "root_cause": "INSUFFICIENT_FUNDS",
        "confidence": 0.98,
        "recovery_potential": "MEDIUM",
        "recommended_intervention": "SEND_EMAIL"
    }

    print("[TEST] Selecting intervention...")
    intervention = select_intervention(test_classification, test_payment)
    print(json.dumps(intervention, indent=2))

    print("\n[TEST] Generating recovery message...")
    message = generate_recovery_message(test_payment, test_classification)
    print(json.dumps(message, indent=2))