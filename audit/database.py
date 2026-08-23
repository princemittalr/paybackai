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
            last_attempted_at TEXT
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
            status TEXT DEFAULT 'running'
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
    """)

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