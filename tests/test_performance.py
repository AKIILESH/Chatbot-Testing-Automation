import pytest
from app.chatbot import ProcurementChatbot
from app.evaluator import ProcureEvaluator
from app.schemas import TestCase


@pytest.mark.asyncio
async def test_response_latency_measurement(chatbot):
    """
    Validates that response latency is accurately recorded and within SLA (< 12000ms).
    """
    _, latency_ms, _ = await chatbot.answer_query("What is the status of PR-1024?")
    assert latency_ms > 0
    assert latency_ms < 12000.0, f"Expected latency under 12000ms, got {latency_ms}ms"


def test_evaluator_flags_excessive_latency(evaluator):
    """
    Validates that the evaluation engine detects and flags excessive response latency exceeding SLA.
    """
    tc = TestCase(
        id="TC-PERF-SLA",
        category="performance",
        name="Strict SLA Performance Test",
        prompt="List approved vendors.",
        expected_answer="TechSource India, Apex Logistics & Cargo, OfficePro Supplies, Precision Motors & Controls.",
        max_allowed_latency_ms=500.0,
    )
    # Simulated excessive latency (1200ms > max 500ms)
    res = evaluator.evaluate_test_case(tc, tc.expected_answer, latency_ms=1200.0)

    assert res.passed is False
    assert res.metrics["response_latency"].passed is False
    assert "exceeded SLA" in res.metrics["response_latency"].reasoning


@pytest.mark.parametrize(
    "query,sla_ms",
    [
        ("What is the status of PR-1025?", 12000.0),
        ("Who is the vendor for PO-2045?", 12000.0),
        ("What is the remaining budget for IT?", 12000.0),
    ],
)
@pytest.mark.asyncio
async def test_parameterized_performance_benchmarks(chatbot, evaluator, query, sla_ms):
    """
    Validates that common procurement inquiries reliably meet configurable SLA targets.
    """
    ans, latency_ms, _ = await chatbot.answer_query(query)
    assert latency_ms <= sla_ms, f"Query '{query}' took {latency_ms}ms, exceeding SLA limit {sla_ms}ms"


def test_groq_service_unconfigured_error_handling():
    """
    Validates that GroqService handles missing credentials gracefully without crashing.
    """
    from app.groq_service import GroqService
    svc = GroqService(api_key="")
    assert svc.is_configured is False

