import sqlite3
import os
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "paybackai.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS failed_payments (
            id TEXT PRIMARY KEY,
            order_id TEXT,
            amount INTEGER,
            currency TEXT DEFAULT 'INR',
            failure_reason TEXT,
            failure_code TEXT,
            customer_email TEXT,
            customer_contact TEXT,
            merchant_id TEXT,
            created_at TEXT,
            status TEXT DEFAULT 'pending',
            retry_count INTEGER DEFAULT 0,
            last_attempted_at TEXT,
            scenario_type TEXT DEFAULT 'payment_failure',
            promise_to_pay TEXT,
            promise_due_date TEXT,
            promise_kept INTEGER DEFAULT 0,
            extra_data TEXT
        );

        CREATE TABLE IF NOT EXISTS recovery_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payment_id TEXT NOT NULL,
            action_type TEXT NOT NULL,
            action_reason TEXT,
            decision_explanation TEXT,
            executed_at TEXT NOT NULL,
            outcome TEXT,
            outcome_detail TEXT,
            FOREIGN KEY (payment_id) REFERENCES failed_payments(id)
        );

        CREATE TABLE IF NOT EXISTS batch_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT UNIQUE NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            total_payments INTEGER DEFAULT 0,
            recovered INTEGER DEFAULT 0,
            failed_recovery INTEGER DEFAULT 0,
            skipped INTEGER DEFAULT 0,
            total_amount_at_risk INTEGER DEFAULT 0,
            total_amount_recovered INTEGER DEFAULT 0,
            status TEXT DEFAULT 'running',
            payment_failures_processed INTEGER DEFAULT 0,
            checkout_abandonments_processed INTEGER DEFAULT 0,
            subscription_failures_processed INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payment_id TEXT,
            event_type TEXT NOT NULL,
            event_data TEXT,
            reasoning TEXT,
            timestamp TEXT NOT NULL,
            run_id TEXT
        );

        CREATE TABLE IF NOT EXISTS promise_tracker (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payment_id TEXT NOT NULL,
            customer_email TEXT,
            customer_contact TEXT,
            amount INTEGER,
            promised_at TEXT NOT NULL,
            promise_due_date TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            followed_up_at TEXT,
            resolved_at TEXT,
            FOREIGN KEY (payment_id) REFERENCES failed_payments(id)
        );

        CREATE TABLE IF NOT EXISTS intervention_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT,
            intervention_type TEXT NOT NULL,
            total_sent INTEGER DEFAULT 0,
            total_recovered INTEGER DEFAULT 0,
            total_amount_recovered INTEGER DEFAULT 0,
            recorded_at TEXT NOT NULL
        );
    """)

    # Migrate existing DB — add new columns if missing
    existing_cols = [row[1] for row in cursor.execute("PRAGMA table_info(failed_payments)").fetchall()]
    new_cols = {
        "scenario_type": "TEXT DEFAULT 'payment_failure'",
        "promise_to_pay": "TEXT",
        "promise_due_date": "TEXT",
        "promise_kept": "INTEGER DEFAULT 0",
        "extra_data": "TEXT"
    }
    for col, col_type in new_cols.items():
        if col not in existing_cols:
            cursor.execute(f"ALTER TABLE failed_payments ADD COLUMN {col} {col_type}")
            print(f"[DB] Migrated: added column {col}")

    existing_batch_cols = [row[1] for row in cursor.execute("PRAGMA table_info(batch_runs)").fetchall()]
    new_batch_cols = {
        "payment_failures_processed": "INTEGER DEFAULT 0",
        "checkout_abandonments_processed": "INTEGER DEFAULT 0",
        "subscription_failures_processed": "INTEGER DEFAULT 0"
    }
    for col, col_type in new_batch_cols.items():
        if col not in existing_batch_cols:
            cursor.execute(f"ALTER TABLE batch_runs ADD COLUMN {col} {col_type}")

    conn.commit()
    conn.close()
    print(f"[DB] Database initialized at {DB_PATH}")


def reset_db():
    if DB_PATH.exists():
        os.remove(DB_PATH)
        print("[DB] Existing database removed.")
    init_db()


if __name__ == "__main__":
    init_db()