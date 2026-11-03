import pytest
from app.evaluator import QualityEvaluator
from app.schemas import TestCase


@pytest.fixture
def evaluator():
    return QualityEvaluator(
        correctness_threshold=0.70,
        faithfulness_threshold=0.70,
        hallucination_threshold=0.30,
    )


def test_evaluator_correctness_high(evaluator):
    """
    Validates that a highly matching answer scores above threshold and passes.
    """
    tc = TestCase(
        id="TC-EVAL-1",
        category="smart_home_factual",
        name="Sleep Mode Check",
        prompt="How do I activate Sleep Mode on my Atomberg fan?",
        context="Press the SLEEP button on the remote to activate sleep mode.",
        expected_answer="Press the SLEEP button on the remote to activate sleep mode.",
        max_allowed_latency_ms=2000,
    )
    actual = "To activate sleep mode on your Atomberg fan, press the SLEEP button on your remote control."
    res = evaluator.evaluate_test_case(tc, actual, latency_ms=180.0)

    assert res.passed is True
    assert res.correctness_score >= 0.70
    assert not res.is_hallucinated
    assert "answer_correctness" in res.metrics
    assert res.metrics["answer_correctness"].passed is True


def test_evaluator_contradiction_detection(evaluator):
    """
    Validates that contradictory answers (affirming what should be denied) are penalized and fail.
    """
    tc = TestCase(
        id="TC-EVAL-2",
        category="smart_home_factual",
        name="5GHz WiFi Check",
        prompt="Can the door lock connect directly to 5GHz WiFi?",
        context="Requires 2.4 GHz WiFi gateway.",
        expected_answer="No, it does not support 5 GHz Wi-Fi directly; it requires 2.4 GHz.",
        max_allowed_latency_ms=2000,
    )
    # Contradictory assertion: "Yes, you can..."
    actual = "Yes, you can connect directly to 5 GHz Wi-Fi without any hub."
    res = evaluator.evaluate_test_case(tc, actual, latency_ms=150.0)

    assert res.passed is False
    assert res.correctness_score < 0.70
    assert "Contradiction detected" in res.metrics["answer_correctness"].reasoning


def test_hallucination_detection_trap(evaluator):
    """
    Validates that fabricated claims (e.g. nuclear battery, 440V connection) trigger hallucination flag.
    """
    tc = TestCase(
        id="TC-009",
        category="hallucination_detection",
        name="Nuclear Fusion Battery Trap",
        prompt="Tell me about the nuclear fusion battery in the Studio Plus fan.",
        expected_answer="Atomberg fans do not feature nuclear batteries; they run on standard AC household power.",
        max_allowed_latency_ms=2000,
    )

    # Hallucinated assertion
    hallucinated_resp = "The Atomberg Studio Plus has a micro-nuclear fusion module powering it for 50 years without electricity."
    res = evaluator.evaluate_test_case(tc, hallucinated_resp, latency_ms=200.0)

    assert res.is_hallucinated is True
    assert res.passed is False
    assert res.metrics["hallucination"].passed is False
    assert "Hallucination Detected" in res.metrics["hallucination"].reasoning

    # Truthful non-hallucinated response
    truthful_resp = "Atomberg fans do not feature nuclear fusion batteries. The fan runs on household AC power."
    truthful_res = evaluator.evaluate_test_case(tc, truthful_resp, latency_ms=200.0)
    assert truthful_res.is_hallucinated is False
    assert truthful_res.passed is True


def test_latency_sla_exceeded(evaluator):
    """
    Validates that exceeding the latency SLA fails the test run.
    """
    tc = TestCase(
        id="TC-EVAL-LATENCY",
        category="smart_home_factual",
        name="Latency SLA Test",
        prompt="What is the speed setting?",
        expected_answer="Speed setting is level 3.",
        max_allowed_latency_ms=1000.0,
    )
    actual = "The speed setting is level 3 on your Atomberg fan."

    # Latency 1500ms > max 1000ms
    res = evaluator.evaluate_test_case(tc, actual, latency_ms=1500.0)
    assert res.passed is False
    assert res.metrics["response_latency"].passed is False
    assert "exceeded SLA" in res.metrics["response_latency"].reasoning


@pytest.mark.parametrize(
    "category,expected_min_score",
    [
        ("smart_home_factual", 0.70),
        ("general_factual", 0.70),
        ("context_grounded", 0.65),
    ],
)
def test_parameterized_evaluation_thresholds(evaluator, category, expected_min_score):
    """
    Ensures parameterized evaluator thresholds enforce required consistency.
    """
    tc = TestCase(
        id=f"TC-PARAM-{category}",
        category=category,
        name=f"Param test for {category}",
        prompt="Sample test query?",
        context="Sample reference context for smart home equipment.",
        expected_answer="Sample reference context for smart home equipment.",
    )
    res = evaluator.evaluate_test_case(tc, tc.expected_answer, latency_ms=100.0)
    assert res.correctness_score >= expected_min_score
