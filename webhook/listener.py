import os
import hmac
import hashlib
import json
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from audit.database import init_db, get_connection
from audit.logger import log_event
from agent.classifier import classify_failure
from agent.stopping_rules import check_stopping_rules
from agent.intervention import select_intervention, generate_recovery_message
from agent.executor import execute_action

load_dotenv()

app = FastAPI(
    title="PaybackAI",
    description="Autonomous payment recovery agent for Razorpay merchants",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

# Auto-seed on startup if database is empty
def _auto_seed_and_run():
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM failed_payments").fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM failed_payments WHERE status='pending'").fetchone()[0]
    conn.close()

    if count == 0:
        print("[STARTUP] Database empty — seeding 60 payments...")
        from data.synthetic import seed_database
        seed_database()
        print("[STARTUP] Seed complete — running batch recovery...")
        import threading
        def run_batch_bg():
            from main import run_batch
            run_batch(limit=60)
        threading.Thread(target=run_batch_bg, daemon=True).start()
        print("[STARTUP] Batch recovery started in background.")
    elif pending > 0:
        print(f"[STARTUP] Found {pending} pending payments — running batch recovery...")
        import threading
        def run_batch_bg():
            from main import run_batch
            run_batch(limit=pending)
        threading.Thread(target=run_batch_bg, daemon=True).start()

_auto_seed_and_run()


def verify_webhook_signature(body: bytes, signature: str) -> bool:
    secret = os.getenv("WEBHOOK_SECRET", "")
    expected = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


async def process_failed_payment_background(payment_data: dict):
    payment_id = payment_data.get("id")
    try:
        conn = get_connection()
        existing = conn.execute(
            "SELECT id FROM failed_payments WHERE id = ?", (payment_id,)
        ).fetchone()

        if not existing:
            conn.execute(
                """
                INSERT INTO failed_payments
                (id, order_id, amount, currency, failure_reason, failure_code,
                 customer_email, customer_contact, merchant_id, created_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
                """,
                (
                    payment_id,
                    payment_data.get("order_id"),
                    payment_data.get("amount"),
                    payment_data.get("currency", "INR"),
                    payment_data.get("error_description", "Unknown failure"),
                    payment_data.get("error_code", "UNKNOWN"),
                    payment_data.get("email", ""),
                    payment_data.get("contact", ""),
                    payment_data.get("merchant_id", ""),
                    datetime.utcnow().isoformat()
                )
            )
            conn.commit()
        conn.close()

        import uuid
        run_id = "webhook_" + uuid.uuid4().hex[:8]
        from main import process_single_payment
        process_single_payment(payment_data, run_id)

    except Exception as e:
        log_event(
            event_type="WEBHOOK_PROCESSING_ERROR",
            payment_id=payment_id,
            event_data={"error": str(e)},
            reasoning="Background processing failed"
        )


@app.get("/")
async def root():
    return {
        "service": "PaybackAI",
        "status": "running",
        "version": "1.0.0",
        "description": "Autonomous payment recovery agent"
    }


@app.get("/health")
async def health():
    conn = get_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM failed_payments"
    ).fetchone()[0]
    conn.close()
    return {
        "status": "healthy",
        "total_payments_tracked": count,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/webhook/razorpay")
async def razorpay_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")

    if not verify_webhook_signature(body, signature):
        log_event(
            event_type="WEBHOOK_SIGNATURE_INVALID",
            event_data={"signature": signature[:20]}
        )
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    payload = json.loads(body)
    event = payload.get("event")

    log_event(
        event_type="WEBHOOK_RECEIVED",
        event_data={"event": event}
    )

    if event == "payment.failed":
        payment_entity = payload["payload"]["payment"]["entity"]
        background_tasks.add_task(
            process_failed_payment_background,
            payment_entity
        )
        return {"status": "accepted", "event": event, "message": "Recovery agent triggered"}

    return {"status": "ignored", "event": event}


@app.get("/api/stats")
async def get_stats():
    conn = get_connection()
    try:
        total = conn.execute("SELECT COUNT(*) FROM failed_payments").fetchone()[0]
        recovered = conn.execute("SELECT COUNT(*) FROM failed_payments WHERE status='recovered'").fetchone()[0]
        skipped = conn.execute("SELECT COUNT(*) FROM failed_payments WHERE status='skipped'").fetchone()[0]
        failed = conn.execute("SELECT COUNT(*) FROM failed_payments WHERE status='failed_recovery'").fetchone()[0]
        pending = conn.execute("SELECT COUNT(*) FROM failed_payments WHERE status='pending'").fetchone()[0]
        total_at_risk = conn.execute("SELECT COALESCE(SUM(amount),0) FROM failed_payments").fetchone()[0]
        total_recovered = conn.execute("SELECT COALESCE(SUM(amount),0) FROM failed_payments WHERE status='recovered'").fetchone()[0]

        # Scenario breakdown
        scenario_breakdown = {}
        for stype in ["payment_failure", "checkout_abandonment", "subscription_failure"]:
            count = conn.execute(
                "SELECT COUNT(*) FROM failed_payments WHERE scenario_type=?", (stype,)
            ).fetchone()[0]
            rec = conn.execute(
                "SELECT COUNT(*) FROM failed_payments WHERE scenario_type=? AND status='recovered'", (stype,)
            ).fetchone()[0]
            amt = conn.execute(
                "SELECT COALESCE(SUM(amount),0) FROM failed_payments WHERE scenario_type=? AND status='recovered'", (stype,)
            ).fetchone()[0]
            scenario_breakdown[stype] = {"total": count, "recovered": rec, "amount_recovered": amt}

        # Intervention effectiveness
        intervention_stats = conn.execute(
            """SELECT action_type,
               COUNT(*) as total,
               SUM(CASE WHEN outcome LIKE '%DISPATCHED%' OR outcome IN ('SUCCESS','SIMULATED_RETRY','MANDATE_RETRY_QUEUED') THEN 1 ELSE 0 END) as successful
               FROM recovery_actions
               GROUP BY action_type
               ORDER BY total DESC"""
        ).fetchall()

        # Promise tracker
        promises_total = conn.execute("SELECT COUNT(*) FROM promise_tracker").fetchone()[0]
        promises_pending = conn.execute("SELECT COUNT(*) FROM promise_tracker WHERE status='pending'").fetchone()[0]

        recent_runs = conn.execute(
            """SELECT run_id, started_at, completed_at, total_payments,
               recovered, failed_recovery, skipped,
               total_amount_at_risk, total_amount_recovered, status,
               payment_failures_processed, checkout_abandonments_processed,
               subscription_failures_processed
               FROM batch_runs ORDER BY started_at DESC LIMIT 5"""
        ).fetchall()

        return {
            "summary": {
                "total_payments": total,
                "recovered": recovered,
                "failed_recovery": failed,
                "skipped": skipped,
                "pending": pending,
                "recovery_rate": round(recovered / total * 100, 2) if total > 0 else 0,
                "total_amount_at_risk_paise": total_at_risk,
                "total_amount_recovered_paise": total_recovered,
                "total_amount_at_risk_rupees": round(total_at_risk / 100, 2),
                "total_amount_recovered_rupees": round(total_recovered / 100, 2),
            },
            "scenario_breakdown": scenario_breakdown,
            "intervention_effectiveness": [dict(r) for r in intervention_stats],
            "promise_tracker": {
                "total": promises_total,
                "pending": promises_pending
            },
            "recent_runs": [dict(r) for r in recent_runs]
        }
    finally:
        conn.close()


@app.get("/api/payments")
async def get_payments(
    status: str = None,
    scenario_type: str = None,
    limit: int = 20,
    offset: int = 0
):
    conn = get_connection()
    try:
        conditions = []
        params = []
        if status:
            conditions.append("status = ?")
            params.append(status)
        if scenario_type:
            conditions.append("scenario_type = ?")
            params.append(scenario_type)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        payments = conn.execute(
            f"SELECT * FROM failed_payments {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (*params, limit, offset)
        ).fetchall()
        return {"payments": [dict(p) for p in payments]}
    finally:
        conn.close()


@app.get("/api/payments/{payment_id}/audit")
async def get_payment_audit(payment_id: str):
    from audit.logger import get_audit_trail, get_recovery_actions
    return {
        "payment_id": payment_id,
        "audit_trail": get_audit_trail(payment_id),
        "recovery_actions": get_recovery_actions(payment_id)
    }


@app.get("/api/batch/{run_id}")
async def get_batch_run(run_id: str):
    from audit.logger import get_batch_summary
    return get_batch_summary(run_id)


@app.post("/api/admin/seed")
async def admin_seed():
    """Seed the database with synthetic failed payments."""
    try:
        from data.synthetic import seed_database
        payments = seed_database()
        return {
            "status": "success",
            "message": f"Seeded {len(payments)} payments",
            "total": len(payments)
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/admin/run-batch")
async def admin_run_batch(limit: int = 60):
    """Run the recovery batch on Railway."""
    try:
        from main import run_batch
        result = run_batch(limit=limit)
        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/admin/reset")
async def admin_reset():
    conn = get_connection()
    try:
        conn.execute("UPDATE failed_payments SET status='pending', retry_count=0, last_attempted_at=NULL")
        conn.commit()
        count = conn.execute("SELECT COUNT(*) FROM failed_payments").fetchone()[0]
        return {"status": "success", "message": f"Reset {count} payments to pending"}
    finally:
        conn.close()


@app.post("/api/admin/hard-reset")
async def admin_hard_reset():
    """Wipe DB and reseed with fresh 80 payments including all scenario types."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM failed_payments")
        conn.execute("DELETE FROM recovery_actions")
        conn.execute("DELETE FROM batch_runs")
        conn.execute("DELETE FROM audit_log")
        conn.execute("DELETE FROM promise_tracker")
        conn.commit()
    finally:
        conn.close()

    from data.synthetic import seed_database
    payments = seed_database()

    scenario_counts = {}
    for p in payments:
        st = p.get("scenario_type", "unknown")
        scenario_counts[st] = scenario_counts.get(st, 0) + 1

    return {
        "status": "success",
        "message": f"Hard reset complete — seeded {len(payments)} fresh payments",
        "scenario_breakdown": scenario_counts
    }

@app.get("/api/debug/groq")
async def debug_groq():
    """Test Groq API key directly."""
    import os
    from groq import Groq
    api_key = os.getenv("GROQ_API_KEY", "NOT_SET")
    key_preview = api_key[:15] + "..." if len(api_key) > 15 else api_key
    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": "Reply with just: OK"}],
            max_tokens=10
        )
        return {
            "status": "success",
            "key_preview": key_preview,
            "key_length": len(api_key),
            "response": response.choices[0].message.content
        }
    except Exception as e:
        return {
            "status": "error",
            "key_preview": key_preview,
            "key_length": len(api_key),
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("webhook.listener:app", host="0.0.0.0", port=8000, reload=True)