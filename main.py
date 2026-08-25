import uuid
import json
from datetime import datetime
from audit.database import init_db, get_connection
from audit.logger import log_event
from agent.classifier import classify_failure
from agent.stopping_rules import check_stopping_rules
from agent.intervention import select_intervention, generate_recovery_message, record_promise_to_pay
from agent.executor import execute_action


def process_single_payment(payment: dict, run_id: str) -> dict:
    payment_id = payment["id"]
    result = {
        "payment_id": payment_id,
        "amount": payment["amount"],
        "scenario_type": payment.get("scenario_type", "payment_failure"),
        "status": None,
        "action_taken": None,
        "outcome": None,
        "reasoning": None,
        "recovered": False
    }

    log_event("PROCESSING_STARTED", payment_id=payment_id,
              event_data={"amount": payment["amount"],
                          "failure_code": payment["failure_code"],
                          "scenario_type": payment.get("scenario_type")},
              reasoning="Payment picked up by recovery agent", run_id=run_id)

    # Step 1: Classify
    classification_result = classify_failure(payment)
    classification = classification_result["classification"]
    log_event("CLASSIFIED", payment_id=payment_id, event_data=classification,
              reasoning=classification.get("reasoning"), run_id=run_id)

    # Step 2: Stopping rules
    stop_check = check_stopping_rules(payment, classification)
    if stop_check["should_stop"]:
        result["status"] = "STOPPED"
        result["action_taken"] = "NO_ACTION"
        result["outcome"] = "STOPPED_BY_RULES"
        result["reasoning"] = " | ".join(stop_check["reasons"])
        log_event("STOPPED_BY_RULES", payment_id=payment_id, event_data=stop_check,
                  reasoning=result["reasoning"], run_id=run_id)
        _update_payment_status(payment_id, "skipped")
        return result

    # Step 3: Intervention
    intervention = select_intervention(classification, payment)
    action = intervention["action"]
    log_event("INTERVENTION_SELECTED", payment_id=payment_id, event_data=intervention,
              reasoning=intervention["reason"], run_id=run_id)

    # Step 4: Promise-to-pay tracking
    record_promise_to_pay(payment, classification, run_id)

    # Step 5: Generate message
    message_data = {}
    if action in ["SEND_EMAIL", "SEND_SMS", "SEND_WHATSAPP", "SEND_CART_RECOVERY"]:
        message_result = generate_recovery_message(payment, classification)
        message_data = message_result.get("message_data", {})

    # Step 6: Execute
    execution_result = execute_action(action=action, payment=payment,
                                      classification=classification,
                                      message_data=message_data, run_id=run_id)

    recovered = execution_result.get("outcome") in [
        "EMAIL_DISPATCHED", "SMS_DISPATCHED", "WHATSAPP_DISPATCHED",
        "CART_RECOVERY_DISPATCHED", "MANDATE_RETRY_QUEUED",
        "SIMULATED_RETRY", "SUCCESS"
    ]

    result["status"] = "PROCESSED"
    result["action_taken"] = action
    result["outcome"] = execution_result.get("outcome")
    result["reasoning"] = classification.get("reasoning")
    result["recovered"] = recovered

    _update_payment_status(payment_id, "recovered" if recovered else "failed_recovery")

    log_event("PROCESSING_COMPLETE", payment_id=payment_id,
              event_data={"outcome": result["outcome"], "recovered": recovered},
              reasoning=f"{action} → {'recovered' if recovered else 'not recovered'}",
              run_id=run_id)

    return result


def _update_payment_status(payment_id: str, status: str):
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE failed_payments SET status=?, retry_count=retry_count+1, last_attempted_at=? WHERE id=?",
            (status, datetime.utcnow().isoformat(), payment_id)
        )
        conn.commit()
    finally:
        conn.close()


def run_batch(limit: int = 10) -> dict:
    run_id = "run_" + uuid.uuid4().hex[:10]
    started_at = datetime.utcnow()

    print(f"\n{'='*60}")
    print(f"  PaybackAI — Batch Recovery Run")
    print(f"  Run ID : {run_id}")
    print(f"  Started: {started_at.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"  Limit  : {limit} payments")
    print(f"{'='*60}\n")

    conn = get_connection()
    conn.execute(
        "INSERT INTO batch_runs (run_id, started_at, status) VALUES (?, ?, 'running')",
        (run_id, started_at.isoformat())
    )
    conn.commit()
    conn.close()

    conn = get_connection()
    payments = conn.execute(
        "SELECT * FROM failed_payments WHERE status='pending' LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    payments = [dict(p) for p in payments]
    total = len(payments)

    if total == 0:
        print("[BATCH] No pending payments.")
        return {}

    print(f"[BATCH] Processing {total} payments\n")

    results = []
    recovered = failed = skipped = 0
    pf_count = ca_count = sf_count = 0
    total_at_risk = sum(p["amount"] for p in payments)
    total_recovered_amount = 0

    for i, payment in enumerate(payments, 1):
        scenario = payment.get("scenario_type", "payment_failure")
        icon = "🛒" if scenario == "checkout_abandonment" else "🔄" if scenario == "subscription_failure" else "💳"
        print(f"[{i:02d}/{total}] {icon} {payment['id']} — ₹{payment['amount']/100:.2f} ({scenario})", end=" ... ")

        result = process_single_payment(payment, run_id)
        results.append(result)

        if scenario == "checkout_abandonment":
            ca_count += 1
        elif scenario == "subscription_failure":
            sf_count += 1
        else:
            pf_count += 1

        if result["recovered"]:
            recovered += 1
            total_recovered_amount += payment["amount"]
            print(f"✓ {result['action_taken']} → {result['outcome']}")
        elif result["status"] == "STOPPED":
            skipped += 1
            print(f"⊘ STOPPED")
        else:
            failed += 1
            print(f"✗ {result['action_taken']} → {result['outcome']}")

    completed_at = datetime.utcnow()
    duration = (completed_at - started_at).total_seconds()
    recovery_rate = (recovered / total * 100) if total > 0 else 0

    conn = get_connection()
    conn.execute(
        """UPDATE batch_runs SET completed_at=?, total_payments=?, recovered=?,
           failed_recovery=?, skipped=?, total_amount_at_risk=?,
           total_amount_recovered=?, status='completed',
           payment_failures_processed=?, checkout_abandonments_processed=?,
           subscription_failures_processed=?
           WHERE run_id=?""",
        (completed_at.isoformat(), total, recovered, failed, skipped,
         total_at_risk, total_recovered_amount,
         pf_count, ca_count, sf_count, run_id)
    )
    conn.commit()
    conn.close()

    print(f"\n{'='*60}")
    print(f"  BATCH COMPLETE — {duration:.1f}s")
    print(f"{'='*60}")
    print(f"  Total     : {total}")
    print(f"  Recovered : {recovered} ({recovery_rate:.1f}%)")
    print(f"  Skipped   : {skipped}")
    print(f"  Failed    : {failed}")
    print(f"  Scenarios : {pf_count} payment failures | {ca_count} cart abandonments | {sf_count} subscription failures")
    print(f"  At risk   : ₹{total_at_risk/100:,.2f}")
    print(f"  Recovered : ₹{total_recovered_amount/100:,.2f}")
    print(f"  Run ID    : {run_id}")
    print(f"{'='*60}\n")

    return {
        "run_id": run_id,
        "total": total,
        "recovered": recovered,
        "skipped": skipped,
        "failed": failed,
        "recovery_rate": round(recovery_rate, 2),
        "total_amount_at_risk": total_at_risk,
        "total_amount_recovered": total_recovered_amount,
        "duration_seconds": duration,
        "scenario_breakdown": {
            "payment_failures": pf_count,
            "checkout_abandonments": ca_count,
            "subscription_failures": sf_count
        }
    }


if __name__ == "__main__":
    init_db()
    run_batch(limit=10)