import pytest
from starlette.testclient import TestClient


def test_health_endpoint(client: TestClient):
    """
    Validates /health endpoint status, response schema, and dataset availability.
    """
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app_name"] == "LLM Quality Tester"
    assert "version" in data
    assert data["total_golden_test_cases"] >= 20
    assert "timestamp" in data


def test_get_test_cases_all(client: TestClient):
    """
    Validates /test-cases returns golden dataset with required fields.
    """
    response = client.get("/test-cases")
    assert response.status_code == 200
    cases = response.json()
    assert len(cases) >= 20
    first = cases[0]
    assert "id" in first
    assert "category" in first
    assert "prompt" in first
    assert "expected_answer" in first


def test_get_test_cases_filtered(client: TestClient):
    """
    Validates filtering test cases by category and security_only flag.
    """
    response = client.get("/test-cases?category=smart_home_factual")
    assert response.status_code == 200
    cases = response.json()
    assert len(cases) > 0
    assert all(c["category"] == "smart_home_factual" for c in cases)

    # Filter security only
    sec_response = client.get("/test-cases?security_only=true")
    assert sec_response.status_code == 200
    sec_cases = sec_response.json()
    assert len(sec_cases) >= 6
    assert all(c["security_sensitive"] or "security" in c["category"] for c in sec_cases)


def test_run_tests_endpoint(client: TestClient):
    """
    Validates POST /run-tests executing a subset of tests with mock provider.
    """
    payload = {
        "use_mock": True,
        "test_ids": ["TC-001", "TC-002"],
    }
    response = client.post("/run-tests", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "run_id" in data
    assert data["total_tests"] == 2
    assert data["passed_tests"] >= 1
    assert "pass_rate" in data
    assert len(data["results"]) == 2

    run_id = data["run_id"]

    # Verify retrieval by run_id
    detail_resp = client.get(f"/results/{run_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["run_id"] == run_id


def test_run_tests_invalid_id(client: TestClient):
    """
    Validates error handling when nonexistent test IDs are requested.
    """
    payload = {
        "use_mock": True,
        "test_ids": ["TC-NONEXISTENT-999"],
    }
    response = client.post("/run-tests", json=payload)
    assert response.status_code == 400


def test_results_not_found(client: TestClient):
    """
    Validates 404 response for invalid run_id.
    """
    response = client.get("/results/run_invalid_999999")
    assert response.status_code == 404


def test_regression_endpoint(client: TestClient):
    """
    Validates GET /regression endpoint returns valid schema structure.
    """
    response = client.get("/regression")
    assert response.status_code == 200
    data = response.json()
    assert "has_comparison" in data
    assert "current_run_id" in data
    assert "status_summary" in data
