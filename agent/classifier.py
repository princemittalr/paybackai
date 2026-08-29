import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

_api_key = os.getenv("GROQ_API_KEY")
if not _api_key:
    raise RuntimeError("GROQ_API_KEY environment variable is not set")
client = Groq(api_key=_api_key)

SYSTEM_PROMPT = """You are PaybackAI's revenue recovery classifier. You analyze three types of revenue loss events:

1. PAYMENT_FAILURE — A payment attempt was made but failed
2. CHECKOUT_ABANDONMENT — A customer started checkout but never completed payment
3. SUBSCRIPTION_FAILURE — A recurring subscription charge failed

For each event, determine:
1. Root cause category
2. Recovery potential
3. Best intervention
4. Clear reasoning

You must respond ONLY with valid JSON. No explanation outside JSON.

Root cause categories:
- INSUFFICIENT_FUNDS: Not enough balance
- CARD_EXPIRED: Card expiry has passed
- BANK_DECLINED: Bank blocked the transaction
- INVALID_DETAILS: Wrong card/UPI details
- NETWORK_ERROR: Technical/gateway timeout
- FRAUD_SUSPECTED: Risk systems flagged this
- CART_ABANDONED: Customer left without paying
- UPI_TIMEOUT: UPI intent not approved in time
- MANDATE_EXPIRED: Subscription mandate expired
- AUTO_DEBIT_FAILED: Bank blocked auto-debit
- UNKNOWN: Cannot determine

Recovery potential: HIGH | MEDIUM | LOW | NONE

Interventions:
- RETRY_PAYMENT: Retry immediately (network errors only)
- SEND_EMAIL: Recovery email
- SEND_SMS: SMS nudge
- SEND_WHATSAPP: Hinglish WhatsApp message
- SEND_CART_RECOVERY: Abandoned cart recovery with deep link
- RETRY_MANDATE: Retry subscription mandate
- ESCALATE_HUMAN: Flag for manual review
- BLACKLIST: Mark as fraud
- NO_ACTION: Nothing can be done

Response schema:
{
  "root_cause": "CATEGORY",
  "confidence": 0.0-1.0,
  "recovery_potential": "HIGH|MEDIUM|LOW|NONE",
  "recommended_intervention": "INTERVENTION",
  "reasoning": "One clear sentence",
  "risk_flags": [],
  "estimated_recovery_probability": 0.0-1.0,
  "urgency": "immediate|within_hour|within_day|low",
  "promise_to_pay_likely": true|false
}"""


def classify_failure(payment: dict) -> dict:
    scenario_type = payment.get("scenario_type", "payment_failure")
    amount_rupees = payment.get("amount", 0) / 100

    user_message = f"""Analyze this revenue loss event:

Scenario Type: {scenario_type.upper()}
Payment ID: {payment['id']}
Amount: ₹{amount_rupees:.2f}
Failure Reason: {payment['failure_reason']}
Failure Code: {payment['failure_code']}
Customer Email: {payment['customer_email']}
Retry Count: {payment['retry_count']}
Created At: {payment['created_at']}
Extra Data: {payment.get('extra_data', 'N/A')}

Respond with JSON only."""

    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.1,
            max_tokens=512,
        )

        raw = response.choices[0].message.content
        if not raw or not raw.strip():
            raise ValueError("LLM returned empty response")
        result = json.loads(raw)

        required_keys = [
            "root_cause", "confidence", "recovery_potential",
            "recommended_intervention", "reasoning",
            "risk_flags", "estimated_recovery_probability"
        ]
        for key in required_keys:
            if key not in result:
                result[key] = "UNKNOWN" if key == "root_cause" else ([] if key == "risk_flags" else 0.5)

        return {
            "payment_id": payment["id"],
            "classification": result,
            "raw_response": raw
        }

    except json.JSONDecodeError as e:
        return {
            "payment_id": payment["id"],
            "classification": {
                "root_cause": "UNKNOWN",
                "confidence": 0.0,
                "recovery_potential": "LOW",
                "recommended_intervention": "ESCALATE_HUMAN",
                "reasoning": f"LLM returned invalid JSON: {str(e)}",
                "risk_flags": ["parse_error"],
                "estimated_recovery_probability": 0.1,
                "urgency": "low",
                "promise_to_pay_likely": False
            },
            "raw_response": None
        }

    except Exception as e:
        return {
            "payment_id": payment["id"],
            "classification": {
                "root_cause": "UNKNOWN",
                "confidence": 0.0,
                "recovery_potential": "LOW",
                "recommended_intervention": "ESCALATE_HUMAN",
                "reasoning": f"Classification error: {str(e)}",
                "risk_flags": ["system_error"],
                "estimated_recovery_probability": 0.1,
                "urgency": "low",
                "promise_to_pay_likely": False
            },
            "raw_response": None
        }