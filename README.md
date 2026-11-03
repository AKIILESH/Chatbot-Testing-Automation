# 📦 ProcureQA — LLM Test Automation Framework for Procurement

An automated AI Quality Engineering and Security Testing framework for an enterprise procurement chatbot powered by **Groq Cloud API** (`Llama 3.3 70B` / `Llama 3.1 8B`) and Python.

The framework automatically evaluates:
- **Functional Correctness & Grounding**: Validates purchase requisition statuses, purchase order amounts, vendor terms, and budget arithmetic.
- **Hallucination & Trap Detection**: Discovers whether the chatbot invents nonexistent POs, fake vendors, unapproved policies, or incorrect financial figures.
- **Adversarial Security Resistance**: Defends against system prompt extraction, approval policy bypasses, confidential vendor bidding leaks, and SQL injection commands.
- **API Robustness & Error Handling**: Asserts contract compliance, HTTP status codes (200, 201, 400, 422, 404), and payload edge cases.
- **Latency & Performance SLA Benchmarks**: Measures execution response times and flags excessive latency against configurable SLA thresholds.

---

## 🏗️ Project Architecture

```
procureqa/
├── app/
│   ├── main.py              # FastAPI endpoints: /health, /chat, /requisitions, /purchase-orders, /run-tests, /results
│   ├── chatbot.py           # Procurement chatbot with RAG context retrieval & Groq integration
│   ├── groq_service.py      # Reusable Groq API service client with error & rate-limit handling
│   ├── procurement_data.py  # Mock procurement database & Indian numbering (lakh/crore) formatter
│   ├── evaluator.py         # Dual-engine evaluation (DeepEval + deterministic factual assertions)
│   ├── test_runner.py       # Automated test suite runner & JSON audit report persistence
│   └── schemas.py           # Pydantic v2 schemas for chat, tests, metrics, and procurement
├── tests/
│   ├── conftest.py          # Pytest fixtures and mock client configurations
│   ├── test_correctness.py  # PR statuses, PO amounts, vendor terms, budget math, and approval policies
│   ├── test_hallucination.py# Nonexistent POs (PO-9999), fake vendors, crypto policies, and financial errors
│   ├── test_security.py     # Prompt injections, approval bypasses, PII & SQL manipulation
│   ├── test_api.py          # REST endpoints, payload validation, status codes, and empty checks
│   └── test_performance.py  # Response latency measurements, SLA thresholds, and timeout handling
├── data/
│   └── procurement.json     # Mock procurement database & 21 golden test cases
├── dashboard/
│   └── app.py               # Modern dark-themed Streamlit QA dashboard
├── reports/                 # JSON test execution audit logs
├── .github/workflows/
│   └── tests.yml            # CI/CD pipeline running deterministic tests without API keys
├── requirements.txt         # Project dependencies including groq and deepeval
├── .env.example             # Configuration template
├── pytest.ini               # Pytest configuration
└── README.md                # Documentation & execution guide
```

---

## ⚡ Groq API Integration

The chatbot integrates with the official **Groq Python SDK** (`groq`):
- Reads configuration dynamically from environment variables (`GROQ_API_KEY`, `GROQ_MODEL`).
- Default model: `llama-3.3-70b-versatile` (high reasoning, ultra-fast inference).
- Alternative model: `llama-3.1-8b-instant` (sub-second evaluation latency).
- Encapsulated inside `app/groq_service.py` with custom exception handling for `groq.RateLimitError`, `groq.APIConnectionError`, and `groq.APIStatusError`.
- **Zero-Dependency Mock Fallback**: When `GROQ_API_KEY` is not present or `USE_MOCK_LLM=true`, the system seamlessly switches to a deterministic procurement mock engine.

---

## 💼 Mock Procurement Knowledge Base

The chatbot is grounded in `data/procurement.json`:
- **Purchase Requisitions**: `PR-1024` (10 Laptops, Rahul, ₹6,50,000, *Pending Manager Approval*), `PR-1025` (*Approved*), `PR-1026` (*Rejected*), `PR-1027` (*Auto-Approved*), `PR-1028` (*Pending Finance Approval*).
- **Purchase Orders**: `PO-2045` (TechSource India, ₹5,80,000, *Issued*), `PO-2046` (*Fulfilled*), `PO-2047` (*Pending Delivery*), `PO-2048` (*Under Legal Review*).
- **Approved Vendors**: `VEN-001` TechSource India (IT Equipment, Net 30), `VEN-002` Apex Logistics, `VEN-003` OfficePro Supplies, `VEN-004` Precision Motors.
- **Department Budgets**: IT (Allocated ₹25,00,000 | Spent ₹14,20,000 | Remaining ₹10,80,000), Facilities, Manufacturing, Operations.
- **Policies**: `POL-001` (Auto-approval up to ₹50,000), `POL-002` (Dept Head approval > ₹50,000), `POL-003` (Finance & GM approval > ₹5,00,000), `POL-004` (Sole-source ban), `POL-005` (Confidentiality).

---

## 🚀 Quickstart & Execution Guide

### 1. Installation
```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
To run with live Groq LLM:
```env
USE_MOCK_LLM=false
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```
*(Leave `USE_MOCK_LLM=true` to run 100% offline without any API keys).*

### 3. Run Pytest Test Suite (38 Tests)
```bash
.venv/bin/pytest -v
```
All 38 automated tests pass in ~2 seconds:
- `tests/test_correctness.py` (PR/PO statuses, vendor terms, budget math, policy rules)
- `tests/test_hallucination.py` (Nonexistent POs, fake vendors, crypto policies, wrong financial sums)
- `tests/test_security.py` (Prompt injection, DAN jailbreaks, system prompt extraction, SQL attacks)
- `tests/test_api.py` (REST contract, empty message 400s, missing field 422s, 404s)
- `tests/test_performance.py` (Response timing, SLA thresholds, Groq unconfigured handling)

### 4. Launch the Streamlit QA Dashboard
```bash
.venv/bin/streamlit run dashboard/app.py --server.port 8501
```
Open **[http://localhost:8501](http://localhost:8501)** to view:
- **Overview & DeepEval Scores**: Answer Relevancy, Faithfulness, Factual Correctness, Hallucination Rate, and Category Charts.
- **Test Suite Execution**: 1-click test execution with status filters, failure explanations, and expandable diagnostics.
- **Security & Policy Defense**: Adversarial audit results across prompt injection vectors.
- **Procurement Data Explorer**: Browse mock purchase requisitions, orders, vendors, budgets, and policies.
- **Interactive Chatbot**: Live chat interface with the Groq-powered assistant.

### 5. Start the FastAPI Server
```bash
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```
Interactive Swagger docs: **[http://localhost:8080/docs](http://localhost:8080/docs)**.

#### Endpoints:
- `GET /health`: Health status, Groq connection, and dataset size.
- `POST /chat`: Query the procurement assistant (`{"message": "What is the status of PR-1024?"}`).
- `GET /requisitions`: Retrieve mock purchase requisition records.
- `GET /purchase-orders`: Retrieve mock purchase orders.
- `POST /run-tests`: Trigger the automated QA test suite.
- `GET /results`: Retrieve historical test run audit reports.

---

## 🔄 CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/tests.yml`):
1. Triggers on pull requests and pushes to `main`.
2. Sets up Python 3.11 and installs dependencies.
3. Executes deterministic tests without requiring external API keys.
4. If `GROQ_API_KEY` is configured as a GitHub Secret, automatically executes live Groq API tests.
5. Produces JUnit XML reports and uploads build artifacts.
