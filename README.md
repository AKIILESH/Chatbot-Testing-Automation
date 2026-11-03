# 📦 ProcureQA — LLM Test Automation Mini Framework

An automated AI Quality Engineering and Security Testing framework for an AI-powered enterprise procurement chatbot.

The framework automatically evaluates:
- **Answer Correctness & Factual Grounding**
- **Hallucination & Nonexistent Entity Detection**
- **Prompt Injection & Adversarial Security Resistance**
- **API Robustness & Error Handling**
- **Response Latency & Performance SLA Benchmarking**

---

## 🏗️ Architecture

```
procureqa/
├── app/
│   ├── main.py              # FastAPI REST backend
│   ├── chatbot.py           # Enterprise procurement chatbot (Live API + Deterministic Mock)
│   ├── procurement_data.py  # Mock procurement database loader & helper utilities
│   ├── evaluator.py         # Dual-engine evaluation (DeepEval + deterministic factual assertions)
│   ├── test_runner.py       # Test suite runner & audit report persistence
│   └── schemas.py           # Pydantic v2 schemas for chat, tests, metrics, and procurement
├── tests/
│   ├── conftest.py          # Pytest fixtures and mock client configurations
│   ├── test_correctness.py  # Requisitions, orders, vendors, budgets, and policies
│   ├── test_hallucination.py# Nonexistent POs, vendors, policies, and unavailable entity handling
│   ├── test_security.py     # Prompt injections, approval bypasses, PII & SQL manipulation
│   ├── test_api.py          # REST endpoints, payload validation, and HTTP status codes
│   └── test_performance.py  # Response latency measurements and configurable SLA enforcement
├── data/
│   └── procurement.json     # Mock procurement database & 21 golden test cases
├── dashboard/
│   └── app.py               # Modern dark-themed Streamlit QA dashboard
├── reports/                 # JSON test execution reports
├── .github/workflows/
│   └── tests.yml            # GitHub Actions CI workflow
├── requirements.txt         # Dependencies (FastAPI, DeepEval, Streamlit, Pytest, etc.)
├── .env.example             # Environment configuration template
└── pytest.ini               # Pytest configuration
```

---

## 💼 Domain & Mock Procurement Knowledge Base

The chatbot is grounded in an enterprise procurement knowledge base (`data/procurement.json`):

1. **Purchase Requisitions (PR)**:
   - `PR-1024`: 10 Laptops, Requester: Rahul (IT), ₹6,50,000, Status: *Pending Manager Approval*
   - `PR-1025`: Ergonomic Chairs, Requester: Priya (Facilities), ₹1,87,500, Status: *Approved*
   - `PR-1026`: Cloud Security, Requester: Vikram, ₹8,20,000, Status: *Rejected (Budget Exceeded)*
   - `PR-1027`: Office Stationery, Requester: Sneha, ₹35,000, Status: *Auto-Approved*
   - `PR-1028`: Factory Assembly Sensors, Requester: Amit, ₹12,00,000, Status: *Pending Finance Approval*

2. **Purchase Orders (PO)**:
   - `PO-2045`: TechSource India, ₹5,80,000, Status: *Issued* (8 Workstations)
   - `PO-2046`: Apex Logistics & Cargo, ₹1,45,000, Status: *Fulfilled*
   - `PO-2047`: OfficePro Supplies, ₹42,000, Status: *Pending Delivery*
   - `PO-2048`: Precision Motors & Controls, ₹9,50,000, Status: *Under Legal Review*

3. **Approved Vendors**:
   - `VEN-001`: TechSource India (IT Equipment, Net 30)
   - `VEN-002`: Apex Logistics & Cargo (Logistics & Freight, Net 15)
   - `VEN-003`: OfficePro Supplies (Office Consumables, Net 30)
   - `VEN-004`: Precision Motors & Controls (Industrial Machinery, Milestone-based)

4. **Department Budgets**:
   - `IT`: Allocated ₹25,00,000 | Spent ₹14,20,000 | Remaining ₹10,80,000
   - `Facilities`: Allocated ₹12,00,000 | Spent ₹6,50,000 | Remaining ₹5,50,000
   - `Manufacturing`: Allocated ₹50,00,000 | Spent ₹31,00,000 | Remaining ₹19,00,000
   - `Operations`: Allocated ₹8,00,000 | Spent ₹3,20,000 | Remaining ₹4,80,000

5. **Procurement Policies**:
   - `POL-001`: Purchases up to ₹50,000 are auto-approved if within budget.
   - `POL-002`: Purchases between ₹50,001 and ₹5,00,000 require Department Head approval and 2 comparative quotes.
   - `POL-003`: Purchases above ₹5,00,000 require Department Head, Finance Controller, and General Manager approval.
   - `POL-004`: Sole-source procurement without comparative bidding is strictly prohibited.
   - `POL-005`: Confidential vendor quotations and profit margins must never be disclosed.

---

## 🧪 Test Automation Framework

### Test Suite Categories (33 Total Automated Pytest Tests)

| Test Module | Coverage |
|---|---|
| `test_correctness.py` | PR statuses, PO amounts, vendor categories, budget arithmetic, and policy approval thresholds |
| `test_hallucination.py` | Nonexistent POs (`PO-9999`), missing vendors (`VEN-999`), fabricated Bitcoin policies, and ungrounded departments |
| `test_security.py` | System prompt extraction, approval policy overrides, confidential bidding margin leakage, and SQL injection defenses |
| `test_api.py` | Valid chat execution, empty message handling (400), missing fields (422), PR/PO filters, and 404 lookups |
| `test_performance.py` | Response latency measurements, SLA threshold assertions (<2000ms), and excessive latency flags |

---

## ⚡ Evaluation Methodology

The framework uses a **hybrid evaluation engine**:
1. **Deterministic Assertions**:
   - Exact entity validation on factual procurement records (PR/PO IDs, rupee amounts in Indian numbering format, statuses).
   - Admission assertions on hallucination trap queries (verifying the chatbot explicitly admits when records are nonexistent).
   - Defensive refusal checks on adversarial prompts.
2. **DeepEval LLM-as-a-Judge**:
   - Pluggable `AnswerRelevancyMetric` and `FaithfulnessMetric` when OpenAI API keys are configured.
   - Transparent reporting on LLM judge biases (position bias, verbosity bias).

---

## 🚀 Quickstart & Setup

### 1. Installation
```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
By default, `USE_MOCK_LLM=true` runs the entire suite **100% offline with zero API keys or external costs**.

---

## 🖥️ Running the Application

### 1. Run the Pytest Test Suite
```bash
.venv/bin/pytest -v
```
*(Runs 33 automated tests across correctness, hallucination, security, API, and performance in ~2s)*

### 2. Launch the Streamlit QA Dashboard
```bash
.venv/bin/streamlit run dashboard/app.py --server.port 8501
```
Open **[http://localhost:8501](http://localhost:8501)** to access:
- **Overview & Metrics**: Total tests, pass rate, avg latency, hallucination rate, and category charts.
- **Test Suite Execution**: 1-click test execution with status filters and individual test failure explanations.
- **Security & Policy Defense**: Adversarial prompt injection audit results.
- **Procurement Data Explorer**: Browse purchase requisitions, orders, vendors, budgets, and policies.
- **Interactive Chatbot**: Live chat interface with the procurement assistant.

### 3. Launch the FastAPI Backend
```bash
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```
Interactive Swagger API documentation: **[http://localhost:8080/docs](http://localhost:8080/docs)**.

#### Endpoints:
- `GET /health`: Health status and dataset count
- `POST /chat`: Query the procurement assistant
- `GET /procurement/requisitions`: View purchase requisitions
- `GET /procurement/orders`: View purchase orders
- `POST /run-tests`: Run the automated evaluation suite
- `GET /results`: Retrieve historical test run audit reports

---

## 🔄 CI/CD Automation

The GitHub Actions workflow (`.github/workflows/tests.yml`):
- Runs automatically on pull requests and pushes to `main`.
- Installs dependencies on Python 3.11.
- Executes the deterministic Pytest suite without requiring external API keys.
- Produces JUnit XML reports and uploads artifacts.
- Fails the build if any correctness, security, or API assertion fails.
