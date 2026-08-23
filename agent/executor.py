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
    log_event(
        event_type="RETRY_ATTEMPTED",
        payment_id=payment_id,
        event_data={"amount": payment["amount"], "retry_count": payment["retry_count"]},
        reasoning="Network error detected — attempting automatic retry",
        run_id=run_id
    )

    try:
        # In test mode, we simulate retry by fetching payment status
        # Real implementation would use Razorpay's retry API
        rzp_payment = razorpay_client.payment.fetch(payment_id)
        current_status = rzp_payment.get("status", "unknown")

        if current_status == "captured":
            outcome = "SUCCESS"
            outcome_detail = "Payment already captured — no retry needed"
        else:
            # Simulate retry outcome based on failure type
            # In production this would call the actual retry endpoint
            outcome = "SIMULATED_RETRY"
            outcome_detail = f"Retry queued for payment {payment_id} (test mode simulation)"

        log_recovery_action(
            payment_id=payment_id,
            action_type="RETRY_PAYMENT",
            action_reason="Network error — transient failure",
            decision_explanation="Automatic retry triggered for network/gateway errors",
            outcome=outcome,
            outcome_detail=outcome_detail
        )

        return {"success": True, "outcome": outcome, "detail": outcome_detail}

    except Exception as e:
        # Payment not found in Razorpay (expected for synthetic data)
        outcome_detail = f"Simulated retry for synthetic payment (test mode): {str(e)[:100]}"
        log_recovery_action(
            payment_id=payment_id,
            action_type="RETRY_PAYMENT",
            action_reason="Network error — transient failure",
            decision_explanation="Automatic retry triggered for network/gateway errors",
            outcome="SIMULATED",
            outcome_detail=outcome_detail
        )
        return {"success": True, "outcome": "SIMULATED", "detail": outcome_detail}


def execute_send_email(payment: dict, message_data: dict, run_id: str = None) -> dict:
    payment_id = payment["id"]

    # In production: integrate with SendGrid/AWS SES
    # In test mode: log the email that WOULD be sent
    email_payload = {
        "to": payment["customer_email"],
        "subject": message_data.get("subject", "Payment Recovery"),
        "message": message_data.get("message", ""),
        "payment_id": payment_id,
        "amount": payment["amount"],
        "sent_at": datetime.utcnow().isoformat()
    }

    log_event(
        event_type="EMAIL_SENT",
        payment_id=payment_id,
        event_data=email_payload,
        reasoning=f"Recovery email sent to {payment['customer_email']}",
        run_id=run_id
    )

    log_recovery_action(
        payment_id=payment_id,
        action_type="SEND_EMAIL",
        action_reason=message_data.get("call_to_action", ""),
        decision_explanation=f"Email dispatched: {message_data.get('subject', '')}",
        outcome="DISPATCHED",
        outcome_detail=f"To: {payment['customer_email']}"
    )

    return {
        "success": True,
        "outcome": "EMAIL_DISPATCHED",
        "detail": f"Recovery email sent to {payment['customer_email']}",
        "payload": email_payload
    }


def execute_send_sms(payment: dict, message_data: dict, run_id: str = None) -> dict:
    payment_id = payment["id"]

    sms_payload = {
        "to": payment.get("customer_contact", "unknown"),
        "message": message_data.get("message", ""),
        "payment_id": payment_id,
        "sent_at": datetime.utcnow().isoformat()
    }

    log_event(
        event_type="SMS_SENT",
        payment_id=payment_id,
        event_data=sms_payload,
        reasoning=f"SMS recovery nudge sent to {payment.get('customer_contact')}",
        run_id=run_id
    )

    log_recovery_action(
        payment_id=payment_id,
        action_type="SEND_SMS",
        action_reason="Bank declined — customer needs alternative payment method",
        decision_explanation=f"SMS sent to {payment.get('customer_contact')}",
        outcome="DISPATCHED",
        outcome_detail=sms_payload["message"][:100]
    )

    return {
        "success": True,
        "outcome": "SMS_DISPATCHED",
        "detail": f"SMS sent to {payment.get('customer_contact')}",
        "payload": sms_payload
    }


def execute_send_whatsapp(payment: dict, message_data: dict, run_id: str = None) -> dict:
    payment_id = payment["id"]

    whatsapp_payload = {
        "to": payment.get("customer_contact", "unknown"),
        "message": message_data.get("message", ""),
        "language": "hinglish",
        "payment_id": payment_id,
        "sent_at": datetime.utcnow().isoformat()
    }

    log_event(
        event_type="WHATSAPP_SENT",
        payment_id=payment_id,
        event_data=whatsapp_payload,
        reasoning="High-value payment — Hinglish WhatsApp nudge for better Indian customer engagement",
        run_id=run_id
    )

    log_recovery_action(
        payment_id=payment_id,
        action_type="SEND_WHATSAPP",
        action_reason="High value payment with insufficient funds",
        decision_explanation="Hinglish WhatsApp message sent for higher engagement rate",
        outcome="DISPATCHED",
        outcome_detail=whatsapp_payload["message"][:100]
    )

    return {
        "success": True,
        "outcome": "WHATSAPP_DISPATCHED",
        "detail": f"Hinglish WhatsApp sent to {payment.get('customer_contact')}",
        "payload": whatsapp_payload
    }


def execute_blacklist(payment: dict, classification: dict, run_id: str = None) -> dict:
    payment_id = payment["id"]

    log_event(
        event_type="BLACKLISTED",
        payment_id=payment_id,
        event_data={
            "reason": "Fraud suspected",
            "confidence": classification.get("confidence"),
            "risk_flags": classification.get("risk_flags", [])
        },
        reasoning="Payment flagged as fraudulent — blacklisted, no recovery attempted",
        run_id=run_id
    )

    log_recovery_action(
        payment_id=payment_id,
        action_type="BLACKLIST",
        action_reason="Fraud detected by classifier",
        decision_explanation="Hard stop — fraud flagged payment must not be retried",
        outcome="BLACKLISTED",
        outcome_detail="Payment marked as fraud — escalated to risk team"
    )

    return {
        "success": True,
        "outcome": "BLACKLISTED",
        "detail": "Payment flagged as fraud and blacklisted"
    }


def execute_escalate(payment: dict, run_id: str = None) -> dict:
    payment_id = payment["id"]

    log_event(
        event_type="ESCALATED",
        payment_id=payment_id,
        event_data={"amount": payment["amount"], "reason": "Unknown failure type"},
        reasoning="Could not determine automated intervention — escalated to human agent",
        run_id=run_id
    )

    log_recovery_action(
        payment_id=payment_id,
        action_type="ESCALATE_HUMAN",
        action_reason="Unknown failure pattern",
        decision_explanation="Automated agent could not classify — human review required",
        outcome="ESCALATED",
        outcome_detail="Added to human review queue"
    )

    return {
        "success": True,
        "outcome": "ESCALATED",
        "detail": "Payment escalated to human review queue"
    }


def execute_action(
    action: str,
    payment: dict,
    classification: dict,
    message_data: dict = None,
    run_id: str = None
) -> dict:
    executors = {
        "RETRY_PAYMENT": lambda: execute_retry(payment, run_id),
        "SEND_EMAIL": lambda: execute_send_email(payment, message_data or {}, run_id),
        "SEND_SMS": lambda: execute_send_sms(payment, message_data or {}, run_id),
        "SEND_WHATSAPP": lambda: execute_send_whatsapp(payment, message_data or {}, run_id),
        "BLACKLIST": lambda: execute_blacklist(payment, classification, run_id),
        "ESCALATE_HUMAN": lambda: execute_escalate(payment, run_id),
        "NO_ACTION": lambda: {"success": True, "outcome": "NO_ACTION", "detail": "No intervention required"},
    }

    executor = executors.get(action)
    if not executor:
        return {"success": False, "outcome": "UNKNOWN_ACTION", "detail": f"Unknown action: {action}"}

    return executor()


if __name__ == "__main__":
    test_payment = {
        "id": "pay_test_executor_001",
        "amount": 99900,
        "customer_email": "priya.sharma@gmail.com",
        "customer_contact": "+919876543210",
        "retry_count": 0,
        "created_at": datetime.utcnow().isoformat()
    }

    test_classification = {
        "root_cause": "INSUFFICIENT_FUNDS",
        "confidence": 0.98,
        "recovery_potential": "MEDIUM",
        "risk_flags": []
    }

    test_message = {
        "subject": "Your payment of ₹999 failed",
        "message": "Hi Priya! Aapka ₹999 ka payment fail ho gaya. Please retry!",
        "call_to_action": "Complete your payment"
    }

    print("[TEST] Executing SEND_EMAIL action...")
    result = execute_action(
        "SEND_EMAIL", test_payment,
        test_classification, test_message,
        run_id="test_run_001"
    )
    print(json.dumps(result, indent=2))

    print("\n[TEST] Executing BLACKLIST action...")
    fraud_payment = {**test_payment, "id": "pay_test_executor_002"}
    fraud_classification = {**test_classification, "root_cause": "FRAUD_SUSPECTED", "risk_flags": ["velocity_abuse"]}
    result2 = execute_action("BLACKLIST", fraud_payment, fraud_classification, run_id="test_run_001")
    print(json.dumps(result2, indent=2))