import pytest
from starlette.testclient import TestClient


def test_health_endpoint(client: TestClient):
    """
    Validates /health response status 200, system name 'ProcureQA', and golden dataset size.
    """
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app_name"] == "ProcureQA"
    assert data["total_golden_test_cases"] >= 20
    assert "version" in data


def test_post_chat_valid(client: TestClient):
    """
    Validates POST /chat with valid procurement message.
    """
    payload = {"message": "What is the status of PR-1024?"}
    response = client.post("/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "latency_ms" in data
    assert "Pending Manager Approval" in data["response"]


def test_post_chat_empty_payload_error(client: TestClient):
    """
    Validates HTTP 400 or 422 error handling on empty or whitespace message.
    """
    response = client.post("/chat", json={"message": "   "})
    assert response.status_code in (400, 422)


def test_post_chat_missing_required_fields(client: TestClient):
    """
    Validates HTTP 422 Unprocessable Entity when required 'message' field is absent.
    """
    response = client.post("/chat", json={})
    assert response.status_code == 422


def test_get_procurement_requisitions(client: TestClient):
    """
    Validates GET /requisitions (and alias /procurement/requisitions) returns requisition list.
    """
    response = client.get("/requisitions")
    assert response.status_code == 200
    prs = response.json()
    assert len(prs) >= 5
    assert any(pr["id"] == "PR-1024" for pr in prs)

    # Filtered
    filtered = client.get("/requisitions?status_filter=Approved")
    assert filtered.status_code == 200
    assert all(pr["status"] == "Approved" for pr in filtered.json())


def test_get_procurement_orders(client: TestClient):
    """
    Validates GET /purchase-orders (and alias /procurement/orders) returns orders.
    """
    response = client.get("/purchase-orders")
    assert response.status_code == 200
    pos = response.json()
    assert len(pos) >= 4
    assert any(po["id"] == "PO-2045" for po in pos)

    # Filtered
    v_filtered = client.get("/purchase-orders?vendor_filter=TechSource")
    assert v_filtered.status_code == 200
    assert all("TechSource" in po["vendor_name"] for po in v_filtered.json())


def test_run_tests_endpoint(client: TestClient):
    """
    Validates POST /run-tests triggers automated test execution and returns HTTP 201 Created.
    """
    payload = {
        "test_ids": ["TC-CORR-01", "TC-HALLUC-01"],
    }
    response = client.post("/run-tests", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["total_tests"] == 2
    assert data["passed_tests"] == 2
    assert data["pass_rate"] == 100.0


def test_get_results_and_not_found(client: TestClient):
    """
    Validates GET /results history and 404 on nonexistent run ID.
    """
    resp = client.get("/results")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

    notFound = client.get("/results/nonexistent_run_99999")
    assert notFound.status_code == 404


def test_invalid_requisition_filter_empty(client: TestClient):
    """
    Validates filtering requisitions with nonexistent status returns empty list.
    """
    resp = client.get("/requisitions?status_filter=NonExistentStatus")
    assert resp.status_code == 200
    assert resp.json() == []
