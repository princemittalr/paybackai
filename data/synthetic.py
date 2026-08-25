import random
import uuid
from datetime import datetime, timedelta

FAILURE_SCENARIOS = [
    {
        "failure_code": "BAD_REQUEST_ERROR",
        "failure_reason": "Your payment was declined due to insufficient funds.",
        "weight": 20,
        "recovery_potential": "high",
        "description": "Insufficient funds",
        "scenario_type": "payment_failure"
    },
    {
        "failure_code": "GATEWAY_ERROR",
        "failure_reason": "Payment failed due to a gateway error. Please try again.",
        "weight": 15,
        "recovery_potential": "high",
        "description": "Gateway timeout/error",
        "scenario_type": "payment_failure"
    },
    {
        "failure_code": "BAD_REQUEST_ERROR",
        "failure_reason": "Your card has expired. Please use a different card.",
        "weight": 10,
        "recovery_potential": "low",
        "description": "Card expired",
        "scenario_type": "payment_failure"
    },
    {
        "failure_code": "BAD_REQUEST_ERROR",
        "failure_reason": "Transaction declined by bank. Please contact your bank.",
        "weight": 10,
        "recovery_potential": "medium",
        "description": "Bank declined",
        "scenario_type": "payment_failure"
    },
    {
        "failure_code": "BAD_REQUEST_ERROR",
        "failure_reason": "Invalid card number entered. Please check and retry.",
        "weight": 8,
        "recovery_potential": "medium",
        "description": "Invalid card details",
        "scenario_type": "payment_failure"
    },
    {
        "failure_code": "GATEWAY_ERROR",
        "failure_reason": "Network error occurred during payment processing.",
        "weight": 8,
        "recovery_potential": "high",
        "description": "Network error",
        "scenario_type": "payment_failure"
    },
    {
        "failure_code": "BAD_REQUEST_ERROR",
        "failure_reason": "Payment blocked due to suspected fraud.",
        "weight": 4,
        "recovery_potential": "none",
        "description": "Fraud suspected",
        "scenario_type": "payment_failure"
    },
    # Checkout abandonment scenarios
    {
        "failure_code": "CHECKOUT_ABANDONED",
        "failure_reason": "Customer added items to cart but did not complete checkout.",
        "weight": 10,
        "recovery_potential": "high",
        "description": "Cart abandonment",
        "scenario_type": "checkout_abandonment"
    },
    {
        "failure_code": "CHECKOUT_ABANDONED",
        "failure_reason": "Customer reached payment page but dropped off before confirming.",
        "weight": 8,
        "recovery_potential": "high",
        "description": "Payment page drop-off",
        "scenario_type": "checkout_abandonment"
    },
    {
        "failure_code": "CHECKOUT_ABANDONED",
        "failure_reason": "Customer started UPI payment but did not approve on app.",
        "weight": 7,
        "recovery_potential": "high",
        "description": "UPI intent abandoned",
        "scenario_type": "checkout_abandonment"
    },
    # Subscription failure scenarios
    {
        "failure_code": "SUBSCRIPTION_FAILED",
        "failure_reason": "Subscription mandate charge failed due to insufficient funds.",
        "weight": 8,
        "recovery_potential": "high",
        "description": "Subscription charge failed",
        "scenario_type": "subscription_failure"
    },
    {
        "failure_code": "SUBSCRIPTION_FAILED",
        "failure_reason": "Subscription renewal failed — mandate expired.",
        "weight": 5,
        "recovery_potential": "medium",
        "description": "Mandate expired",
        "scenario_type": "subscription_failure"
    },
    {
        "failure_code": "SUBSCRIPTION_FAILED",
        "failure_reason": "Subscription payment failed — customer bank declined auto-debit.",
        "weight": 5,
        "recovery_potential": "medium",
        "description": "Auto-debit declined",
        "scenario_type": "subscription_failure"
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

SUBSCRIPTION_PLANS = [
    "Basic Monthly", "Pro Monthly", "Enterprise Annual",
    "Student Plan", "Family Plan", "Business Pro"
]

CART_ITEMS = [
    "Nike Air Max Shoes", "iPhone 15 Case", "Organic Coffee Pack",
    "React JS Course", "Annual Gym Membership", "Smart Watch Band",
    "Flight Ticket - DEL to BOM", "Hotel Booking - Goa",
    "Monthly Grocery Box", "Premium OTT Subscription"
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


def generate_subscription_id():
    return "sub_" + uuid.uuid4().hex[:14]


def generate_synthetic_failures(count: int = 80) -> list:
    random.seed(42)
    payments = []
    base_time = datetime.utcnow() - timedelta(hours=48)

    for i in range(count):
        scenario = weighted_choice(FAILURE_SCENARIOS)
        customer_name = random.choice(CUSTOMER_NAMES)
        first_name = customer_name.split()[0].lower()
        scenario_type = scenario["scenario_type"]

        # Amount varies by scenario type
        if scenario_type == "subscription_failure":
            amount = random.choice([19900, 29900, 49900, 99900, 199900, 299900])
        elif scenario_type == "checkout_abandonment":
            amount = random.choice([
                49900, 99900, 149900, 199900, 299900,
                499900, 999900, 1499900, 1999900
            ])
        else:
            amount = random.choice([
                499, 999, 1499, 1999, 2999, 4999,
                5999, 9999, 14999, 19999, 24999, 49999
            ])

        created_at = base_time + timedelta(minutes=i * 36)

        # Extra metadata per scenario type
        extra_data = {}
        if scenario_type == "checkout_abandonment":
            extra_data = {
                "cart_item": random.choice(CART_ITEMS),
                "cart_value": amount,
                "drop_off_stage": random.choice([
                    "cart", "address", "payment_method", "upi_intent"
                ])
            }
        elif scenario_type == "subscription_failure":
            extra_data = {
                "subscription_id": generate_subscription_id(),
                "plan_name": random.choice(SUBSCRIPTION_PLANS),
                "billing_cycle": random.choice(["monthly", "annual"]),
                "retry_sequence": random.randint(1, 3)
            }

        payment = {
            "id": generate_payment_id(),
            "order_id": generate_order_id(),
            "amount": amount,
            "currency": "INR",
            "failure_reason": scenario["failure_reason"],
            "failure_code": scenario["failure_code"],
            "failure_description": scenario["description"],
            "recovery_potential": scenario["recovery_potential"],
            "scenario_type": scenario_type,
            "customer_email": f"{first_name}.{random.randint(10,99)}@gmail.com",
            "customer_contact": f"+91{''.join([str(random.randint(0,9)) for _ in range(10)])}",
            "customer_name": customer_name,
            "merchant_id": f"merchant_{random.choice(MERCHANT_CATEGORIES)}",
            "created_at": created_at.isoformat(),
            "status": "pending",
            "retry_count": 0,
            "last_attempted_at": None,
            "promise_to_pay": None,
            "promise_due_date": None,
            "promise_kept": None,
            "extra_data": str(extra_data) if extra_data else None
        }
        payments.append(payment)

    return payments


def seed_database():
    from audit.database import get_connection, init_db
    init_db()
    payments = generate_synthetic_failures(80)
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
        print(f"[SEED] Inserted {inserted} synthetic payments into database.")
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