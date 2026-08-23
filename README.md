# ⚡ PaybackAI — Autonomous Payment Recovery Agent

> **Razorpay AI Buildathon — Track 03: AI Revenue Recovery**

PaybackAI is a fully autonomous AI agent that detects failed payments, classifies root causes using LLM reasoning, and executes compliant multi-channel recovery workflows — with hard stopping rules, Hinglish WhatsApp nudges, fraud detection, and a complete per-payment audit trail.

**No human in the loop. Every decision explained. Every rupee tracked.**

---

## 📊 Live Results — 60 Payments Processed

| Metric | Value |
|--------|-------|
| Total payments processed | 60 |
| Successfully recovered | 35 **(58.33%)** |
| Total amount at risk | ₹6,524.40 |
| Total amount recovered | ₹3,154.65 |
| Fraud payments hard-stopped | 1 |
| Stopping rules checked per payment | 7 |
| Test suite | 43/43 passing |

---

## 🎯 The Problem

Indian merchants lose crores every month to failed payments — insufficient funds, gateway timeouts, expired cards, bank declines. Most have zero automated recovery. Revenue just leaks silently.

**PaybackAI fixes this. Autonomously. With full compliance.**

---

## 🏗️ System Architecture

```
Razorpay webhook (payment.failed event)
            │
            ▼
┌─────────────────────────────────────────┐
│         FastAPI Webhook Listener         │
│         webhook/listener.py             │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│            PaybackAI Agent              │
│                                         │
│  ① CLASSIFIER  (LLM via Groq)          │
│     • Root cause detection              │
│     • Confidence score (0.0 – 1.0)     │
│     • Recovery potential rating         │
│     • Structured JSON reasoning         │
│                                         │
│  ② STOPPING RULES ENGINE (7 checks)    │
│     • Max 3 retries hard limit          │
│     • 7-day payment age cutoff          │
│     • Fraud → immediate hard stop       │
│     • No contact 10pm – 8am IST         │
│     • Confidence threshold < 0.3        │
│     • Minimum amount check              │
│     • Recovery potential = NONE         │
│                                         │
│  ③ INTERVENTION SELECTOR               │
│     • RETRY_PAYMENT (network errors)    │
│     • SEND_EMAIL (card/funds issues)    │
│     • SEND_SMS (bank declines)          │
│     • SEND_WHATSAPP in Hinglish         │
│       (high-value Indian customers)     │
│     • BLACKLIST (fraud)                 │
│     • ESCALATE_HUMAN (unknown)          │
│                                         │
│  ④ EXECUTOR + AUDIT LOGGER             │
│     • Every action written to SQLite    │
│     • LLM reasoning preserved per step  │
│     • Outcome tracked per payment       │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│      Next.js Real-Time Dashboard        │
│  • Recovery rate, amounts, fraud count  │
│  • Per-payment audit trail drawer       │
│  • Batch run history charts             │
└─────────────────────────────────────────┘
```

---

## 🛡️ Compliance — Every Money Action Is:

| Principle | Implementation |
|-----------|----------------|
| **Explainable** | LLM reasoning logged for every classification decision |
| **Bounded** | Max 3 retries, 7-day window, hard amount minimums |
| **Gated** | Fraud payments hard-stopped before any action is taken |
| **Time-restricted** | No customer contact between 10pm – 8am IST |
| **Auditable** | Full SQLite audit trail: every event, timestamp, and reason |
| **Failure-handled** | LLM parse errors → fallback to ESCALATE_HUMAN, never silent fail |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- [Razorpay test account](https://dashboard.razorpay.com/signup) (free)
- [Groq API key](https://console.groq.com) (free)

### 1. Clone & Setup Backend

```bash
git clone https://github.com/princemittalr/paybackai.git
cd paybackai

python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Add your RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, GROQ_API_KEY
```

### 2. Seed Data & Run Agent

```bash
# Generate 60 synthetic failed payments
python3.11 -m data.synthetic

# Run autonomous batch recovery
python3.11 -m main

# Start API + webhook server
python3.11 -m uvicorn webhook.listener:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Start Dashboard

```bash
cd dashboard
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

---

## 📁 Project Structure

```
paybackai/
├── agent/
│   ├── classifier.py       # LLM root cause classifier (Groq)
│   ├── intervention.py     # Channel selector + Hinglish message generator
│   ├── executor.py         # Action executor with full audit logging
│   └── stopping_rules.py   # 7 compliance guardrails
├── audit/
│   ├── database.py         # SQLite schema — 4 tables
│   └── logger.py           # Audit trail + recovery action logger
├── webhook/
│   └── listener.py         # FastAPI server + Razorpay webhook handler
├── data/
│   └── synthetic.py        # 60 synthetic failed payments (weighted scenarios)
├── dashboard/              # Next.js 16 + Tailwind + Recharts
├── tests/
│   └── test_batch.py       # 43 tests, 43 passing
├── main.py                 # Batch orchestrator
├── requirements.txt
└── .env.example
```

---

## 🔌 API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health + payment count |
| `/api/stats` | GET | Full recovery metrics + batch history |
| `/api/payments` | GET | Payments list with status filter |
| `/api/payments/{id}/audit` | GET | Complete audit trail for one payment |
| `/api/batch/{run_id}` | GET | Single batch run details |
| `/webhook/razorpay` | POST | Signed Razorpay webhook receiver |

---

## 🧠 LLM Decision Flow (Per Payment)

```
1. Build context → failure code, amount, retry count, customer info
2. Call Groq LLM → returns structured JSON:
   {
     "root_cause": "INSUFFICIENT_FUNDS",
     "confidence": 0.98,
     "recovery_potential": "MEDIUM",
     "recommended_intervention": "SEND_EMAIL",
     "reasoning": "Explicit insufficient funds message...",
     "risk_flags": [],
     "estimated_recovery_probability": 0.60
   }
3. Run 7 stopping rules → stop or proceed
4. Select intervention channel → decision matrix
5. Generate recovery message → LLM writes Hinglish/English copy
6. Execute action → log outcome + reasoning to SQLite
```

---

## 🛠️ Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Language | Python 3.11 | Best LLM + async ecosystem |
| LLM | Groq `openai/gpt-oss-120b` | Fast, free tier, structured JSON |
| Payments | Razorpay Test Mode API | Native Indian payment infrastructure |
| Backend | FastAPI + Uvicorn | Async, production-grade, auto-docs |
| Database | SQLite | Zero-setup portable audit store |
| Frontend | Next.js 16 + Tailwind CSS | Production-grade UI |
| Charts | Recharts | Native React data visualization |
| Tests | pytest | 43/43 passing |

---

## 🗄️ Database Schema

```sql
failed_payments      -- Payment records + status tracking
recovery_actions     -- Every action taken per payment + outcome
batch_runs           -- Batch-level metrics and run history
audit_log            -- Full event log with LLM reasoning
```

---

## ⚠️ Graceful Failure Handling

| Failure Mode | Behaviour |
|-------------|-----------|
| LLM returns invalid JSON | Fallback to ESCALATE_HUMAN, logged |
| Groq API timeout | Exception caught, error logged, escalated |
| Payment not found in Razorpay | Simulated outcome logged, no crash |
| Fraud detected | Hard stop, blacklisted, never retried |
| Confidence below 0.3 | Stopping rule triggers, escalated |
| Contact outside hours | Deferred, logged with reason |

---

## 🧪 Test Suite

```bash
python3.11 -m pytest tests/test_batch.py -v
# 43 passed in 0.53s
```

Coverage includes:
- Database operations and schema validation
- Audit trail isolation and ordering
- All 7 stopping rules individually
- Every intervention type mapping
- Executor actions and audit logging
- LLM classifier with mocked responses
- Error handling (invalid JSON, API failures)
- Full end-to-end pipeline tests

---

## 👤 Author

**Prince Mittal**
Razorpay AI Buildathon 2026 — Track 03: AI Revenue Recovery
[GitHub](https://github.com/princemittalr/paybackai)