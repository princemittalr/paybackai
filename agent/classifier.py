import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

_api_key = os.getenv("GROQ_API_KEY")
if not _api_key:
    raise RuntimeError("GROQ_API_KEY environment variable is not set")
client = Groq(api_key=_api_key)

SYSTEM_PROMPT = """You are PaybackAI's payment failure classifier. Your job is to analyze failed payments and determine:
1. The root cause category
2. Recovery potential
3. Recommended intervention
4. Clear reasoning

You must respond ONLY with valid JSON. No explanation outside the JSON.

Root cause categories:
- INSUFFICIENT_FUNDS: Customer doesn't have enough balance
- CARD_EXPIRED: Card expiry date has passed
- BANK_DECLINED: Bank blocked the transaction
- INVALID_DETAILS: Wrong card number, CVV, or expiry entered
- NETWORK_ERROR: Technical/gateway timeout, retry likely to succeed
- FRAUD_SUSPECTED: Risk systems flagged this transaction
- UNKNOWN: Cannot determine from available information

Recovery potential:
- HIGH: Strong chance of recovery with right intervention
- MEDIUM: Possible but uncertain
- LOW: Unlikely but worth one attempt
- NONE: Do not attempt recovery

Interventions:
- RETRY_PAYMENT: Attempt payment again (only for NETWORK_ERROR or GATEWAY issues)
- SEND_EMAIL: Send recovery email to customer
- SEND_SMS: Send SMS nudge (for high-value payments)
- SEND_WHATSAPP: Send WhatsApp message in Hinglish for Indian customers
- ESCALATE_HUMAN: Flag for manual review
- BLACKLIST: Mark as fraud, do not recover
- NO_ACTION: Nothing can be done

Your JSON response must follow this exact schema:
{
  "root_cause": "CATEGORY",
  "confidence": 0.0-1.0,
  "recovery_potential": "HIGH|MEDIUM|LOW|NONE",
  "recommended_intervention": "INTERVENTION",
  "reasoning": "One clear sentence explaining the decision",
  "risk_flags": [],
  "estimated_recovery_probability": 0.0-1.0
}"""


def classify_failure(payment: dict) -> dict:
    user_message = f"""Analyze this failed payment and classify it:

Payment ID: {payment['id']}
Amount: ₹{payment['amount'] / 100:.2f}
Failure Reason: {payment['failure_reason']}
Failure Code: {payment['failure_code']}
Customer Email: {payment['customer_email']}
Retry Count: {payment['retry_count']}
Created At: {payment['created_at']}

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
            response_format={"type": "json_object"}
        )

        raw = response.choices[0].message.content
        result = json.loads(raw)

        required_keys = [
            "root_cause", "confidence", "recovery_potential",
            "recommended_intervention", "reasoning",
            "risk_flags", "estimated_recovery_probability"
        ]
        for key in required_keys:
            if key not in result:
                raise ValueError(f"Missing key in LLM response: {key}")

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
                "estimated_recovery_probability": 0.1
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
                "estimated_recovery_probability": 0.1
            },
            "raw_response": None
        }


if __name__ == "__main__":
    test_payment = {
        "id": "pay_test_001",
        "amount": 99900,
        "failure_reason": "Your payment was declined due to insufficient funds.",
        "failure_code": "BAD_REQUEST_ERROR",
        "customer_email": "test@gmail.com",
        "retry_count": 0,
        "created_at": "2024-01-15T10:30:00"
    }

    print("[TEST] Classifying a single payment...")
    result = classify_failure(test_payment)
    print(json.dumps(result, indent=2))