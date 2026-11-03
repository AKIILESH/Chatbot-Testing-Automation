import pytest
from starlette.testclient import TestClient
from app.main import app
from app.chatbot import ProcurementChatbot
from app.evaluator import ProcureEvaluator
from app.test_runner import TestRunner
from app.schemas import TestCase


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@pytest.fixture
def chatbot():
    return ProcurementChatbot(use_mock=True)


@pytest.fixture
def evaluator():
    return ProcureEvaluator(
        correctness_threshold=0.70,
        faithfulness_threshold=0.70,
        hallucination_threshold=0.30,
    )


@pytest.fixture
def isolated_runner(tmp_path, chatbot, evaluator):
    tmp_reports = tmp_path / "reports"
    tmp_reports.mkdir(parents=True, exist_ok=True)
    return TestRunner(reports_dir=str(tmp_reports), chatbot=chatbot, evaluator=evaluator)


@pytest.fixture
def sample_pr_test_case():
    return TestCase(
        id="TC-FIXTURE-PR",
        category="correctness",
        name="Fixture PR-1024 Check",
        prompt="What is the status of PR-1024?",
        expected_answer="Purchase requisition PR-1024 is currently 'Pending Manager Approval' with estimated cost ₹6,50,000.",
        security_sensitive=False,
        max_allowed_latency_ms=2000,
    )
