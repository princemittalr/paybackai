import random
import uuid
from datetime import datetime, timedelta

FAILURE_SCENARIOS = [
    {
        "failure_code": "BAD_REQUEST_ERROR",
        "failure_reason": "Your payment was declined due to insufficient funds.",
        "weight": 25,
        "recovery_potential": "high",
        "description": "Insufficient funds"
    },
    {
        "failure_code": "GATEWAY_ERROR",
        "failure_reason": "Payment failed due to a gateway error. Please try again.",
        "weight": 20,
        "recovery_potential": "high",
        "description": "Gateway timeout/error"
    },
    {
        "failure_code": "BAD_REQUEST_ERROR",
        "failure_reason": "Your card has expired. Please use a different card.",
        "weight": 15,
        "recovery_potential": "low",
        "description": "Card expired"
    },
    {
        "failure_code": "BAD_REQUEST_ERROR",
        "failure_reason": "Transaction declined by bank. Please contact your bank.",
        "weight": 15,
        "recovery_potential": "medium",
        "description": "Bank declined"
    },
    {
        "failure_code": "BAD_REQUEST_ERROR",
        "failure_reason": "Invalid card number entered. Please check and retry.",
        "weight": 10,
        "recovery_potential": "medium",
        "description": "Invalid card details"
    },
    {
        "failure_code": "GATEWAY_ERROR",
        "failure_reason": "Network error occurred during payment processing.",
        "weight": 10,
        "recovery_potential": "high",
        "description": "Network error"
    },
    {
        "failure_code": "BAD_REQUEST_ERROR",
        "failure_reason": "Payment blocked due to suspected fraud.",
        "weight": 5,
        "recovery_potential": "none",
        "description": "Fraud suspected"
    },
]

CUSTOMER_NAMES = [
    "Aarav Shah", "Priya Patel", "Rohit Sharma", "Sneha Gupta",
    "Vikram Singh", "Ananya Nair", "Rahul Verma", "Pooja Iyer",
    "Arjun Mehta", "Kavya Reddy", "Amit Kumar", "Divya Joshi",
    "Nikhil Bose", "Shreya Agarwal", "Karan Malhotra", "Riya Chopra",
    "Siddharth Rao", "Meera Nambiar", "Harsh Tiwari", "Nisha Pillai"
]

MERCHANT_CATEGORIES = [
    "e-commerce", "saas", "edtech", "food-delivery", "travel"
]


def weighted_choice(scenarios):
    total = sum(s["weight"] for s in scenarios)
    r = random.uniform(0, total)
    cumulative = 0
    for s in scenarios:
        cumulative += s["weight"]
        if r <= cumulative:
            return s
    return scenarios[-1]


def generate_payment_id():
    return "pay_" + uuid.uuid4().hex[:14]


def generate_order_id():
    return "order_" + uuid.uuid4().hex[:14]


def generate_synthetic_failures(count: int = 60) -> list:
    random.seed(42)
    payments = []
    base_time = datetime.utcnow() - timedelta(hours=24)

    for i in range(count):
        scenario = weighted_choice(FAILURE_SCENARIOS)
        customer_name = random.choice(CUSTOMER_NAMES)
        first_name = customer_name.split()[0].lower()
        amount = random.choice([
            499, 999, 1499, 1999, 2499, 2999, 3999, 4999,
            5999, 7999, 9999, 14999, 19999, 24999, 49999
        ])
        created_at = base_time + timedelta(minutes=i * 24)

        payment = {
            "id": generate_payment_id(),
            "order_id": generate_order_id(),
            "amount": amount,
            "currency": "INR",
            "failure_reason": scenario["failure_reason"],
            "failure_code": scenario["failure_code"],
            "failure_description": scenario["description"],
            "recovery_potential": scenario["recovery_potential"],
            "customer_email": f"{first_name}.{random.randint(10,99)}@gmail.com",
            "customer_contact": f"+91{''.join([str(random.randint(0,9)) for _ in range(10)])}",
            "customer_name": customer_name,
            "merchant_id": f"merchant_{random.choice(MERCHANT_CATEGORIES)}",
            "created_at": created_at.isoformat(),
            "status": "pending",
            "retry_count": 0,
            "last_attempted_at": None
        }
        payments.append(payment)

    return payments


def seed_database():
    from audit.database import get_connection, init_db
    init_db()
    payments = generate_synthetic_failures(60)
    conn = get_connection()
    inserted = 0
    try:
        for p in payments:
            try:
                conn.execute(
                    """
                    INSERT INTO failed_payments
                    (id, order_id, amount, currency, failure_reason, failure_code,
                     customer_email, customer_contact, merchant_id, created_at,
                     status, retry_count, last_attempted_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        p["id"], p["order_id"], p["amount"], p["currency"],
                        p["failure_reason"], p["failure_code"],
                        p["customer_email"], p["customer_contact"],
                        p["merchant_id"], p["created_at"],
                        p["status"], p["retry_count"], p["last_attempted_at"]
                    )
                )
                inserted += 1
            except Exception as e:
                print(f"[SEED] Skipping {p['id']}: {e}")
        conn.commit()
        print(f"[SEED] Inserted {inserted} synthetic failed payments into database.")
    finally:
        conn.close()

    return payments


if __name__ == "__main__":
    seed_database()
    from audit.database import get_connection
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM failed_payments").fetchone()[0]
    total_risk = conn.execute("SELECT SUM(amount) FROM failed_payments").fetchone()[0]
    conn.close()
    print(f"[SEED] Total payments in DB: {count}")
    print(f"[SEED] Total amount at risk: ₹{total_risk/100:,.2f}")