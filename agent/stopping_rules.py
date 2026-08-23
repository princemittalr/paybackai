from datetime import datetime, timedelta

MAX_RETRIES = 3
MAX_AGE_HOURS = 168
MIN_AMOUNT_PAISE = 100
FRAUD_CODES = ["FRAUD_SUSPECTED", "BLACKLIST"]
STOP_HOUR_START = 22
STOP_HOUR_END = 8


def check_stopping_rules(payment: dict, classification: dict) -> dict:
    reasons = []
    now = datetime.utcnow()

    # Rule 1: Max retry limit
    if payment.get("retry_count", 0) >= MAX_RETRIES:
        reasons.append(f"Max retry limit reached ({MAX_RETRIES} attempts)")

    # Rule 2: Payment too old
    try:
        created_at = datetime.fromisoformat(payment["created_at"])
        age_hours = (now - created_at).total_seconds() / 3600
        if age_hours > MAX_AGE_HOURS:
            reasons.append(f"Payment too old ({age_hours:.1f}h > {MAX_AGE_HOURS}h limit)")
    except Exception:
        reasons.append("Could not parse payment creation time")

    # Rule 3: Amount too small
    if payment.get("amount", 0) < MIN_AMOUNT_PAISE:
        reasons.append(f"Amount too small to recover (₹{payment['amount']/100:.2f})")

    # Rule 4: Fraud flagged — hard stop
    root_cause = classification.get("root_cause", "")
    if root_cause in FRAUD_CODES:
        reasons.append(f"Fraud flagged: {root_cause} — hard stop, no recovery attempted")

    # Rule 5: Zero recovery potential
    if classification.get("recovery_potential") == "NONE":
        reasons.append("Recovery potential is NONE per classifier")

    # Rule 6: Do not contact outside allowed hours (10pm - 8am IST)
    ist_hour = (now.hour + 5) % 24
    if ist_hour >= STOP_HOUR_START or ist_hour < STOP_HOUR_END:
        reasons.append(f"Outside contact hours (IST {ist_hour}:00 — allowed 08:00-22:00)")

    # Rule 7: Confidence too low
    if classification.get("confidence", 1.0) < 0.0:
        reasons.append(f"Classifier confidence too low ({classification.get('confidence')})")

    should_stop = len(reasons) > 0

    return {
        "should_stop": should_stop,
        "reasons": reasons,
        "checked_at": now.isoformat(),
        "rules_applied": [
            "max_retries", "max_age", "min_amount",
            "fraud_check", "recovery_potential",
            "contact_hours", "confidence_threshold"
        ]
    }


if __name__ == "__main__":
    import json

    test_payment = {
        "id": "pay_test_001",
        "amount": 99900,
        "retry_count": 0,
        "created_at": datetime.utcnow().isoformat()
    }

    test_classification = {
        "root_cause": "INSUFFICIENT_FUNDS",
        "confidence": 0.98,
        "recovery_potential": "MEDIUM",
        "recommended_intervention": "SEND_EMAIL"
    }

    result = check_stopping_rules(test_payment, test_classification)
    print(json.dumps(result, indent=2))

    print("\n--- Testing fraud hard stop ---")
    fraud_classification = {
        "root_cause": "FRAUD_SUSPECTED",
        "confidence": 0.95,
        "recovery_potential": "NONE",
        "recommended_intervention": "BLACKLIST"
    }
    result2 = check_stopping_rules(test_payment, fraud_classification)
    print(json.dumps(result2, indent=2))