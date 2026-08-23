"""
PaybackAI — Automated Test Suite
Tests the complete agent pipeline with assertions.
Run with: python3.11 -m pytest tests/test_batch.py -v
"""

import pytest
import json
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock


# ─────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────

@pytest.fixture(autouse=True)
def use_test_db(tmp_path, monkeypatch):
    """Redirect all DB operations to a temp database for tests."""
    test_db = tmp_path / "test_paybackai.db"
    monkeypatch.setattr("audit.database.DB_PATH", test_db)
    from audit.database import init_db
    init_db()
    yield test_db


@pytest.fixture
def valid_payment():
    return {
        "id": f"pay_{uuid.uuid4().hex[:14]}",
        "order_id": f"order_{uuid.uuid4().hex[:14]}",
        "amount": 99900,
        "currency": "INR",
        "failure_reason": "Your payment was declined due to insufficient funds.",
        "failure_code": "BAD_REQUEST_ERROR",
        "customer_email": "priya.sharma@gmail.com",
        "customer_contact": "+919876543210",
        "merchant_id": "merchant_ecommerce",
        "created_at": datetime.utcnow().isoformat(),
        "status": "pending",
        "retry_count": 0,
        "last_attempted_at": None
    }


@pytest.fixture
def network_error_payment():
    return {
        "id": f"pay_{uuid.uuid4().hex[:14]}",
        "order_id": f"order_{uuid.uuid4().hex[:14]}",
        "amount": 49900,
        "currency": "INR",
        "failure_reason": "Payment failed due to a gateway error. Please try again.",
        "failure_code": "GATEWAY_ERROR",
        "customer_email": "rahul.v@gmail.com",
        "customer_contact": "+919812345678",
        "merchant_id": "merchant_saas",
        "created_at": datetime.utcnow().isoformat(),
        "status": "pending",
        "retry_count": 0,
        "last_attempted_at": None
    }


@pytest.fixture
def fraud_payment():
    return {
        "id": f"pay_{uuid.uuid4().hex[:14]}",
        "order_id": f"order_{uuid.uuid4().hex[:14]}",
        "amount": 999900,
        "currency": "INR",
        "failure_reason": "Payment blocked due to suspected fraud.",
        "failure_code": "BAD_REQUEST_ERROR",
        "customer_email": "suspicious@tempmail.com",
        "customer_contact": "+919999999999",
        "merchant_id": "merchant_ecommerce",
        "created_at": datetime.utcnow().isoformat(),
        "status": "pending",
        "retry_count": 0,
        "last_attempted_at": None
    }


@pytest.fixture
def expired_card_payment():
    return {
        "id": f"pay_{uuid.uuid4().hex[:14]}",
        "order_id": f"order_{uuid.uuid4().hex[:14]}",
        "amount": 29900,
        "currency": "INR",
        "failure_reason": "Your card has expired. Please use a different card.",
        "failure_code": "BAD_REQUEST_ERROR",
        "customer_email": "kavya.r@gmail.com",
        "customer_contact": "+919876001234",
        "merchant_id": "merchant_edtech",
        "created_at": datetime.utcnow().isoformat(),
        "status": "pending",
        "retry_count": 0,
        "last_attempted_at": None
    }


@pytest.fixture
def high_value_payment():
    return {
        "id": f"pay_{uuid.uuid4().hex[:14]}",
        "order_id": f"order_{uuid.uuid4().hex[:14]}",
        "amount": 999900,
        "currency": "INR",
        "failure_reason": "Your payment was declined due to insufficient funds.",
        "failure_code": "BAD_REQUEST_ERROR",
        "customer_email": "arjun.mehta@gmail.com",
        "customer_contact": "+919988776655",
        "merchant_id": "merchant_travel",
        "created_at": datetime.utcnow().isoformat(),
        "status": "pending",
        "retry_count": 0,
        "last_attempted_at": None
    }


# ─────────────────────────────────────────────
# DATABASE TESTS
# ─────────────────────────────────────────────

class TestDatabase:

    def test_tables_created(self):
        from audit.database import get_connection
        conn = get_connection()
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = [t[0] for t in tables]
        conn.close()

        assert "failed_payments" in table_names
        assert "recovery_actions" in table_names
        assert "batch_runs" in table_names
        assert "audit_log" in table_names

    def test_insert_and_fetch_payment(self, valid_payment):
        from audit.database import get_connection
        conn = get_connection()
        conn.execute(
            """INSERT INTO failed_payments
               (id, order_id, amount, currency, failure_reason, failure_code,
                customer_email, customer_contact, merchant_id, created_at,
                status, retry_count, last_attempted_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                valid_payment["id"], valid_payment["order_id"],
                valid_payment["amount"], valid_payment["currency"],
                valid_payment["failure_reason"], valid_payment["failure_code"],
                valid_payment["customer_email"], valid_payment["customer_contact"],
                valid_payment["merchant_id"], valid_payment["created_at"],
                valid_payment["status"], valid_payment["retry_count"],
                valid_payment["last_attempted_at"]
            )
        )
        conn.commit()

        row = conn.execute(
            "SELECT * FROM failed_payments WHERE id=?", (valid_payment["id"],)
        ).fetchone()
        conn.close()

        assert row is not None
        assert row["amount"] == 99900
        assert row["status"] == "pending"
        assert row["retry_count"] == 0

    def test_payment_status_update(self, valid_payment):
        from audit.database import get_connection
        conn = get_connection()
        conn.execute(
            """INSERT INTO failed_payments
               (id, order_id, amount, currency, failure_reason, failure_code,
                customer_email, customer_contact, merchant_id, created_at,
                status, retry_count, last_attempted_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                valid_payment["id"], valid_payment["order_id"],
                valid_payment["amount"], valid_payment["currency"],
                valid_payment["failure_reason"], valid_payment["failure_code"],
                valid_payment["customer_email"], valid_payment["customer_contact"],
                valid_payment["merchant_id"], valid_payment["created_at"],
                "pending", 0, None
            )
        )
        conn.commit()
        conn.execute(
            "UPDATE failed_payments SET status='recovered', retry_count=1 WHERE id=?",
            (valid_payment["id"],)
        )
        conn.commit()

        row = conn.execute(
            "SELECT * FROM failed_payments WHERE id=?", (valid_payment["id"],)
        ).fetchone()
        conn.close()

        assert row["status"] == "recovered"
        assert row["retry_count"] == 1


# ─────────────────────────────────────────────
# AUDIT LOGGER TESTS
# ─────────────────────────────────────────────

class TestAuditLogger:

    def test_log_event(self, valid_payment):
        from audit.logger import log_event, get_audit_trail
        log_event(
            event_type="TEST_EVENT",
            payment_id=valid_payment["id"],
            event_data={"test": True},
            reasoning="This is a test event",
            run_id="test_run_001"
        )
        trail = get_audit_trail(valid_payment["id"])
        assert len(trail) == 1
        assert trail[0]["event_type"] == "TEST_EVENT"
        assert trail[0]["reasoning"] == "This is a test event"

    def test_log_multiple_events_ordered(self, valid_payment):
        from audit.logger import log_event, get_audit_trail
        for i, event in enumerate(["PROCESSING_STARTED", "CLASSIFIED", "PROCESSING_COMPLETE"]):
            log_event(
                event_type=event,
                payment_id=valid_payment["id"],
                event_data={"step": i},
                run_id="test_run_002"
            )

        trail = get_audit_trail(valid_payment["id"])
        assert len(trail) == 3
        assert trail[0]["event_type"] == "PROCESSING_STARTED"
        assert trail[1]["event_type"] == "CLASSIFIED"
        assert trail[2]["event_type"] == "PROCESSING_COMPLETE"

    def test_log_recovery_action(self, valid_payment):
        from audit.logger import log_recovery_action, get_recovery_actions
        log_recovery_action(
            payment_id=valid_payment["id"],
            action_type="SEND_EMAIL",
            action_reason="Insufficient funds",
            decision_explanation="Email sent to customer",
            outcome="EMAIL_DISPATCHED",
            outcome_detail="To: priya.sharma@gmail.com"
        )
        actions = get_recovery_actions(valid_payment["id"])
        assert len(actions) == 1
        assert actions[0]["action_type"] == "SEND_EMAIL"
        assert actions[0]["outcome"] == "EMAIL_DISPATCHED"

    def test_audit_trail_isolation(self, valid_payment):
        """Events for one payment must not appear in another payment's trail."""
        from audit.logger import log_event, get_audit_trail
        other_id = f"pay_{uuid.uuid4().hex[:14]}"
        log_event("EVENT_A", payment_id=valid_payment["id"])
        log_event("EVENT_B", payment_id=other_id)

        trail_a = get_audit_trail(valid_payment["id"])
        trail_b = get_audit_trail(other_id)

        assert len(trail_a) == 1
        assert trail_a[0]["event_type"] == "EVENT_A"
        assert len(trail_b) == 1
        assert trail_b[0]["event_type"] == "EVENT_B"


# ─────────────────────────────────────────────
# STOPPING RULES TESTS
# ─────────────────────────────────────────────

class TestStoppingRules:

    def test_valid_payment_passes_all_rules(self, valid_payment):
        from agent.stopping_rules import check_stopping_rules
        classification = {
            "root_cause": "INSUFFICIENT_FUNDS",
            "confidence": 0.95,
            "recovery_potential": "MEDIUM"
        }
        result = check_stopping_rules(valid_payment, classification)
        assert result["should_stop"] is False
        assert len(result["reasons"]) == 0

    def test_max_retries_triggers_stop(self, valid_payment):
        from agent.stopping_rules import check_stopping_rules
        valid_payment["retry_count"] = 3
        classification = {"root_cause": "INSUFFICIENT_FUNDS", "confidence": 0.9, "recovery_potential": "MEDIUM"}
        result = check_stopping_rules(valid_payment, classification)
        assert result["should_stop"] is True
        assert any("retry" in r.lower() for r in result["reasons"])

    def test_fraud_triggers_hard_stop(self, valid_payment):
        from agent.stopping_rules import check_stopping_rules
        classification = {
            "root_cause": "FRAUD_SUSPECTED",
            "confidence": 0.98,
            "recovery_potential": "NONE"
        }
        result = check_stopping_rules(valid_payment, classification)
        assert result["should_stop"] is True
        assert any("fraud" in r.lower() for r in result["reasons"])

    def test_old_payment_triggers_stop(self, valid_payment):
        from agent.stopping_rules import check_stopping_rules
        valid_payment["created_at"] = (
            datetime.utcnow() - timedelta(hours=200)
        ).isoformat()
        classification = {"root_cause": "INSUFFICIENT_FUNDS", "confidence": 0.9, "recovery_potential": "HIGH"}
        result = check_stopping_rules(valid_payment, classification)
        assert result["should_stop"] is True
        assert any("old" in r.lower() for r in result["reasons"])

    def test_zero_recovery_potential_triggers_stop(self, valid_payment):
        from agent.stopping_rules import check_stopping_rules
        classification = {
            "root_cause": "UNKNOWN",
            "confidence": 0.9,
            "recovery_potential": "NONE"
        }
        result = check_stopping_rules(valid_payment, classification)
        assert result["should_stop"] is True
        assert any("none" in r.lower() for r in result["reasons"])

    def test_low_confidence_triggers_stop(self, valid_payment):
        from agent.stopping_rules import check_stopping_rules
        classification = {
            "root_cause": "UNKNOWN",
            "confidence": 0.1,
            "recovery_potential": "HIGH"
        }
        result = check_stopping_rules(valid_payment, classification)
        assert result["should_stop"] is True
        assert any("confidence" in r.lower() for r in result["reasons"])

    def test_all_rules_listed_in_output(self, valid_payment):
        from agent.stopping_rules import check_stopping_rules
        classification = {"root_cause": "INSUFFICIENT_FUNDS", "confidence": 0.9, "recovery_potential": "MEDIUM"}
        result = check_stopping_rules(valid_payment, classification)
        assert "rules_applied" in result
        assert len(result["rules_applied"]) == 7


# ─────────────────────────────────────────────
# INTERVENTION SELECTOR TESTS
# ─────────────────────────────────────────────

class TestInterventionSelector:

    def test_fraud_maps_to_blacklist(self, fraud_payment):
        from agent.intervention import select_intervention
        classification = {"root_cause": "FRAUD_SUSPECTED", "recovery_potential": "NONE"}
        result = select_intervention(classification, fraud_payment)
        assert result["action"] == "BLACKLIST"
        assert result["priority"] == "critical"

    def test_network_error_maps_to_retry(self, network_error_payment):
        from agent.intervention import select_intervention
        classification = {"root_cause": "NETWORK_ERROR", "recovery_potential": "HIGH"}
        result = select_intervention(classification, network_error_payment)
        assert result["action"] == "RETRY_PAYMENT"
        assert result["priority"] == "high"

    def test_expired_card_maps_to_email(self, expired_card_payment):
        from agent.intervention import select_intervention
        classification = {"root_cause": "CARD_EXPIRED", "recovery_potential": "LOW"}
        result = select_intervention(classification, expired_card_payment)
        assert result["action"] == "SEND_EMAIL"

    def test_high_value_insufficient_funds_maps_to_whatsapp(self, high_value_payment):
        from agent.intervention import select_intervention
        classification = {"root_cause": "INSUFFICIENT_FUNDS", "recovery_potential": "MEDIUM"}
        result = select_intervention(classification, high_value_payment)
        assert result["action"] == "SEND_WHATSAPP"
        assert result["priority"] == "high"

    def test_low_value_insufficient_funds_maps_to_email(self, valid_payment):
        from agent.intervention import select_intervention
        valid_payment["amount"] = 9900  # ₹99 — below WhatsApp threshold
        classification = {"root_cause": "INSUFFICIENT_FUNDS", "recovery_potential": "MEDIUM"}
        result = select_intervention(classification, valid_payment)
        assert result["action"] == "SEND_EMAIL"

    def test_bank_declined_maps_to_sms(self, valid_payment):
        from agent.intervention import select_intervention
        classification = {"root_cause": "BANK_DECLINED", "recovery_potential": "MEDIUM"}
        result = select_intervention(classification, valid_payment)
        assert result["action"] == "SEND_SMS"

    def test_no_recovery_potential_maps_to_no_action(self, valid_payment):
        from agent.intervention import select_intervention
        classification = {"root_cause": "UNKNOWN", "recovery_potential": "NONE"}
        result = select_intervention(classification, valid_payment)
        assert result["action"] == "NO_ACTION"

    def test_intervention_always_has_reason(self, valid_payment):
        from agent.intervention import select_intervention
        for root_cause in ["INSUFFICIENT_FUNDS", "CARD_EXPIRED", "NETWORK_ERROR",
                           "BANK_DECLINED", "FRAUD_SUSPECTED", "INVALID_DETAILS"]:
            classification = {"root_cause": root_cause, "recovery_potential": "MEDIUM"}
            result = select_intervention(classification, valid_payment)
            assert "reason" in result
            assert len(result["reason"]) > 0


# ─────────────────────────────────────────────
# EXECUTOR TESTS
# ─────────────────────────────────────────────

class TestExecutor:

    def test_execute_email_action(self, valid_payment):
        from agent.executor import execute_action
        message_data = {
            "subject": "Your payment failed",
            "message": "Please retry your payment",
            "call_to_action": "Retry now"
        }
        result = execute_action(
            "SEND_EMAIL", valid_payment,
            {"root_cause": "INSUFFICIENT_FUNDS", "risk_flags": []},
            message_data, run_id="test_run"
        )
        assert result["success"] is True
        assert result["outcome"] == "EMAIL_DISPATCHED"

    def test_execute_sms_action(self, valid_payment):
        from agent.executor import execute_action
        message_data = {"message": "Aapka payment fail ho gaya. Please retry!"}
        result = execute_action(
            "SEND_SMS", valid_payment,
            {"root_cause": "BANK_DECLINED", "risk_flags": []},
            message_data, run_id="test_run"
        )
        assert result["success"] is True
        assert result["outcome"] == "SMS_DISPATCHED"

    def test_execute_whatsapp_action(self, valid_payment):
        from agent.executor import execute_action
        message_data = {"message": "Hi! Aapka ₹999 ka payment fail hua. Retry karein!"}
        result = execute_action(
            "SEND_WHATSAPP", valid_payment,
            {"root_cause": "INSUFFICIENT_FUNDS", "risk_flags": []},
            message_data, run_id="test_run"
        )
        assert result["success"] is True
        assert result["outcome"] == "WHATSAPP_DISPATCHED"

    def test_execute_blacklist_action(self, fraud_payment):
        from agent.executor import execute_action
        result = execute_action(
            "BLACKLIST", fraud_payment,
            {"root_cause": "FRAUD_SUSPECTED", "confidence": 0.98, "risk_flags": ["velocity_abuse"]},
            run_id="test_run"
        )
        assert result["success"] is True
        assert result["outcome"] == "BLACKLISTED"

    def test_execute_no_action(self, valid_payment):
        from agent.executor import execute_action
        result = execute_action(
            "NO_ACTION", valid_payment,
            {"root_cause": "UNKNOWN", "risk_flags": []},
            run_id="test_run"
        )
        assert result["success"] is True
        assert result["outcome"] == "NO_ACTION"

    def test_execute_unknown_action_returns_error(self, valid_payment):
        from agent.executor import execute_action
        result = execute_action(
            "INVALID_ACTION", valid_payment,
            {"root_cause": "UNKNOWN", "risk_flags": []},
            run_id="test_run"
        )
        assert result["success"] is False
        assert "UNKNOWN_ACTION" in result["outcome"]

    def test_executor_logs_to_audit(self, valid_payment):
        from agent.executor import execute_action
        from audit.logger import get_recovery_actions
        message_data = {"subject": "Test", "message": "Test msg", "call_to_action": "Test"}
        execute_action(
            "SEND_EMAIL", valid_payment,
            {"root_cause": "INSUFFICIENT_FUNDS", "risk_flags": []},
            message_data, run_id="test_run"
        )
        actions = get_recovery_actions(valid_payment["id"])
        assert len(actions) >= 1
        assert actions[0]["action_type"] == "SEND_EMAIL"


# ─────────────────────────────────────────────
# LLM CLASSIFIER TESTS (mocked)
# ─────────────────────────────────────────────

class TestClassifier:

    def test_classifier_returns_required_keys(self, valid_payment):
        mock_response = {
            "root_cause": "INSUFFICIENT_FUNDS",
            "confidence": 0.95,
            "recovery_potential": "MEDIUM",
            "recommended_intervention": "SEND_EMAIL",
            "reasoning": "Insufficient funds detected",
            "risk_flags": [],
            "estimated_recovery_probability": 0.6
        }
        with patch("agent.classifier.client") as mock_client:
            mock_client.chat.completions.create.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content=json.dumps(mock_response)))]
            )
            from agent.classifier import classify_failure
            result = classify_failure(valid_payment)

        assert "classification" in result
        assert "payment_id" in result
        classification = result["classification"]
        for key in ["root_cause", "confidence", "recovery_potential",
                    "recommended_intervention", "reasoning",
                    "risk_flags", "estimated_recovery_probability"]:
            assert key in classification

    def test_classifier_handles_invalid_json(self, valid_payment):
        with patch("agent.classifier.client") as mock_client:
            mock_client.chat.completions.create.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content="NOT VALID JSON {{{{"))]
            )
            from agent.classifier import classify_failure
            result = classify_failure(valid_payment)

        assert result["classification"]["root_cause"] == "UNKNOWN"
        assert result["classification"]["recommended_intervention"] == "ESCALATE_HUMAN"
        assert "parse_error" in result["classification"]["risk_flags"]

    def test_classifier_handles_api_error(self, valid_payment):
        with patch("agent.classifier.client") as mock_client:
            mock_client.chat.completions.create.side_effect = Exception("API unavailable")
            from agent.classifier import classify_failure
            result = classify_failure(valid_payment)

        assert result["classification"]["root_cause"] == "UNKNOWN"
        assert result["classification"]["recommended_intervention"] == "ESCALATE_HUMAN"
        assert "system_error" in result["classification"]["risk_flags"]

    def test_classifier_confidence_in_valid_range(self, valid_payment):
        mock_response = {
            "root_cause": "GATEWAY_ERROR",
            "confidence": 0.88,
            "recovery_potential": "HIGH",
            "recommended_intervention": "RETRY_PAYMENT",
            "reasoning": "Gateway timeout detected",
            "risk_flags": [],
            "estimated_recovery_probability": 0.75
        }
        with patch("agent.classifier.client") as mock_client:
            mock_client.chat.completions.create.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content=json.dumps(mock_response)))]
            )
            from agent.classifier import classify_failure
            result = classify_failure(valid_payment)

        confidence = result["classification"]["confidence"]
        assert 0.0 <= confidence <= 1.0


# ─────────────────────────────────────────────
# SYNTHETIC DATA TESTS
# ─────────────────────────────────────────────

class TestSyntheticData:

    def test_generates_correct_count(self):
        from data.synthetic import generate_synthetic_failures
        payments = generate_synthetic_failures(60)
        assert len(payments) == 60

    def test_all_payments_have_required_fields(self):
        from data.synthetic import generate_synthetic_failures
        payments = generate_synthetic_failures(10)
        required = ["id", "order_id", "amount", "currency", "failure_reason",
                    "failure_code", "customer_email", "customer_contact",
                    "merchant_id", "created_at", "status", "retry_count"]
        for p in payments:
            for field in required:
                assert field in p, f"Missing field: {field}"

    def test_payment_ids_are_unique(self):
        from data.synthetic import generate_synthetic_failures
        payments = generate_synthetic_failures(60)
        ids = [p["id"] for p in payments]
        assert len(ids) == len(set(ids))

    def test_amounts_are_positive(self):
        from data.synthetic import generate_synthetic_failures
        payments = generate_synthetic_failures(60)
        for p in payments:
            assert p["amount"] > 0

    def test_all_start_as_pending(self):
        from data.synthetic import generate_synthetic_failures
        payments = generate_synthetic_failures(10)
        for p in payments:
            assert p["status"] == "pending"
            assert p["retry_count"] == 0

    def test_fraud_scenario_present_in_large_batch(self):
        from data.synthetic import generate_synthetic_failures
        payments = generate_synthetic_failures(60)
        fraud_payments = [
            p for p in payments
            if "fraud" in p["failure_reason"].lower()
        ]
        assert len(fraud_payments) > 0


# ─────────────────────────────────────────────
# END-TO-END PIPELINE TEST (mocked LLM)
# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
# END-TO-END PIPELINE TEST (mocked LLM)
# ─────────────────────────────────────────────

class TestEndToEndPipeline:

    def test_full_pipeline_insufficient_funds(self, valid_payment):
        mock_classification = {
            "root_cause": "INSUFFICIENT_FUNDS",
            "confidence": 0.95,
            "recovery_potential": "MEDIUM",
            "recommended_intervention": "SEND_EMAIL",
            "reasoning": "Insufficient funds",
            "risk_flags": [],
            "estimated_recovery_probability": 0.6
        }
        mock_message = {
            "channel": "SEND_WHATSAPP",
            "subject": None,
            "message": "Aapka ₹999 ka payment fail hua. Please retry!",
            "tone": "empathetic",
            "call_to_action": "Retry payment"
        }

        with patch("agent.classifier.client") as mock_llm, \
             patch("agent.intervention.client") as mock_msg:

            mock_llm.chat.completions.create.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content=json.dumps(mock_classification)))]
            )
            mock_msg.chat.completions.create.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content=json.dumps(mock_message)))]
            )

            from main import process_single_payment
            result = process_single_payment(valid_payment, run_id="e2e_test_001")

        assert result["status"] == "PROCESSED"
        assert result["action_taken"] in ["SEND_EMAIL", "SEND_WHATSAPP"]
        assert result["recovered"] is True

    def test_full_pipeline_fraud_hard_stop(self, fraud_payment):
        mock_classification = {
            "root_cause": "FRAUD_SUSPECTED",
            "confidence": 0.97,
            "recovery_potential": "NONE",
            "recommended_intervention": "BLACKLIST",
            "reasoning": "Fraud indicators detected",
            "risk_flags": ["velocity_abuse"],
            "estimated_recovery_probability": 0.0
        }

        with patch("agent.classifier.client") as mock_llm:
            mock_llm.chat.completions.create.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content=json.dumps(mock_classification)))]
            )
            from main import process_single_payment
            result = process_single_payment(fraud_payment, run_id="e2e_test_002")

        assert result["status"] in ["STOPPED", "PROCESSED"]
        assert result["action_taken"] in ["NO_ACTION", "BLACKLIST"]
        assert result["recovered"] is False

    def test_full_pipeline_max_retries_stops(self, valid_payment):
        valid_payment["retry_count"] = 3
        mock_classification = {
            "root_cause": "INSUFFICIENT_FUNDS",
            "confidence": 0.9,
            "recovery_potential": "MEDIUM",
            "recommended_intervention": "SEND_EMAIL",
            "reasoning": "Insufficient funds",
            "risk_flags": [],
            "estimated_recovery_probability": 0.5
        }

        with patch("agent.classifier.client") as mock_llm:
            mock_llm.chat.completions.create.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content=json.dumps(mock_classification)))]
            )
            from main import process_single_payment
            result = process_single_payment(valid_payment, run_id="e2e_test_003")

        assert result["status"] == "STOPPED"
        assert result["outcome"] == "STOPPED_BY_RULES"

    def test_audit_trail_written_per_payment(self, valid_payment):
        mock_classification = {
            "root_cause": "INSUFFICIENT_FUNDS",
            "confidence": 0.95,
            "recovery_potential": "MEDIUM",
            "recommended_intervention": "SEND_EMAIL",
            "reasoning": "Insufficient funds",
            "risk_flags": [],
            "estimated_recovery_probability": 0.6
        }
        mock_message = {
            "channel": "SEND_EMAIL",
            "subject": "Test",
            "message": "Test",
            "tone": "empathetic",
            "call_to_action": "Retry"
        }

        with patch("agent.classifier.client") as mock_llm, \
             patch("agent.intervention.client") as mock_msg:
            mock_llm.chat.completions.create.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content=json.dumps(mock_classification)))]
            )
            mock_msg.chat.completions.create.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content=json.dumps(mock_message)))]
            )
            from main import process_single_payment
            process_single_payment(valid_payment, run_id="e2e_test_004")

        from audit.logger import get_audit_trail
        trail = get_audit_trail(valid_payment["id"])
        event_types = [e["event_type"] for e in trail]

        assert "PROCESSING_STARTED" in event_types
        assert "CLASSIFIED" in event_types
        assert "PROCESSING_COMPLETE" in event_types