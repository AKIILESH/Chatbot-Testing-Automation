import pytest
import shutil
from pathlib import Path
from starlette.testclient import TestClient
from app.main import app
from app.test_runner import TestRunner
from app.evaluator import QualityEvaluator
from app.llm_client import LLMClient
from app.regression import RegressionDetector
from app.schemas import TestCase


@pytest.fixture(scope="session")
def client():
    """
    Synchronous FastAPI test client.
    """
    return TestClient(app)


@pytest.fixture
def tmp_reports_dir(tmp_path):
    """
    Isolated temporary reports directory for testing.
    """
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    return str(reports_dir)


@pytest.fixture
def isolated_runner(tmp_reports_dir):
    """
    TestRunner instance pointing to isolated temporary storage and mock LLM.
    """
    mock_client = LLMClient(use_mock=True)
    evaluator = QualityEvaluator()
    return TestRunner(
        reports_dir=tmp_reports_dir,
        llm_client=mock_client,
        evaluator=evaluator,
    )


@pytest.fixture
def isolated_regression_detector(isolated_runner):
    return RegressionDetector(test_runner=isolated_runner)


@pytest.fixture
def sample_test_case():
    return TestCase(
        id="TC-FIXTURE-1",
        category="smart_home_factual",
        name="Fixture Test Fan Speed",
        prompt="How do I set the fan to speed 3?",
        context="Press the 3 button on the remote to set speed 3.",
        expected_answer="Press button 3 on your Atomberg remote control.",
        security_sensitive=False,
        max_allowed_latency_ms=2500,
    )
