import json
from datetime import datetime
from audit.database import get_connection


def log_event(
    event_type: str,
    payment_id: str = None,
    event_data: dict = None,
    reasoning: str = None,
    run_id: str = None
):
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO audit_log (payment_id, event_type, event_data, reasoning, timestamp, run_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                payment_id,
                event_type,
                json.dumps(event_data) if event_data else None,
                reasoning,
                datetime.utcnow().isoformat(),
                run_id
            )
        )
        conn.commit()
    finally:
        conn.close()


def log_recovery_action(
    payment_id: str,
    action_type: str,
    action_reason: str,
    decision_explanation: str,
    outcome: str = None,
    outcome_detail: str = None
):
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO recovery_actions
            (payment_id, action_type, action_reason, decision_explanation, executed_at, outcome, outcome_detail)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payment_id,
                action_type,
                action_reason,
                decision_explanation,
                datetime.utcnow().isoformat(),
                outcome,
                outcome_detail
            )
        )
        conn.commit()
    finally:
        conn.close()


def get_audit_trail(payment_id: str) -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT * FROM audit_log
            WHERE payment_id = ?
            ORDER BY timestamp ASC
            """,
            (payment_id,)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_recovery_actions(payment_id: str) -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT * FROM recovery_actions
            WHERE payment_id = ?
            ORDER BY executed_at ASC
            """,
            (payment_id,)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_batch_summary(run_id: str) -> dict:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM batch_runs WHERE run_id = ?",
            (run_id,)
        ).fetchone()
        return dict(row) if row else {}
    finally:
        conn.close()