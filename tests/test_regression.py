import pytest
import datetime
from app.regression import RegressionDetector
from app.schemas import TestSuiteRun, TestResult


def make_sample_run(run_id: str, pass_rate: float, avg_latency: float, failing_ids=None):
    failing_ids = failing_ids or []
    results = []
    test_ids = ["TC-001", "TC-002", "TC-003", "TC-004"]
    for tid in test_ids:
        passed = tid not in failing_ids
        results.append(
            TestResult(
                test_id=tid,
                name=f"Test {tid}",
                category="smart_home_factual",
                prompt="Sample prompt",
                expected_answer="Sample expected",
                actual_response="Sample response",
                latency_ms=avg_latency,
                passed=passed,
                is_hallucinated=False,
                security_sensitive=False,
            )
        )

    passed_count = sum(1 for r in results if r.passed)
    return TestSuiteRun(
        run_id=run_id,
        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        model_name="mock-aura",
        is_mock=True,
        total_tests=len(results),
        passed_tests=passed_count,
        failed_tests=len(results) - passed_count,
        pass_rate=pass_rate,
        avg_latency_ms=avg_latency,
        hallucination_rate=0.0,
        results=results,
    )


def test_regression_detection_quality_degraded(isolated_regression_detector):
    """
    Validates detection of quality degradation and newly failing tests.
    """
    # Baseline run: 100% pass rate
    baseline_run = make_sample_run("run_baseline", pass_rate=100.0, avg_latency=150.0, failing_ids=[])

    # Current run: 75% pass rate (TC-002 broke)
    current_run = make_sample_run("run_current", pass_rate=75.0, avg_latency=160.0, failing_ids=["TC-002"])

    report = isolated_regression_detector.compare_runs(current_run=current_run, previous_run=baseline_run)

    assert report.has_comparison is True
    assert report.quality_degraded is True
    assert report.pass_rate_delta == -25.0
    assert any("TC-002" in fail_desc for fail_desc in report.newly_failing_tests)
    assert "QUALITY REGRESSION DETECTED" in report.status_summary


def test_regression_detection_latency_increase(isolated_regression_detector):
    """
    Validates detection of response latency increases.
    """
    # Baseline run: 150ms
    baseline_run = make_sample_run("run_baseline", pass_rate=100.0, avg_latency=150.0)

    # Current run: 350ms (+200ms jump, >20% increase)
    current_run = make_sample_run("run_current", pass_rate=100.0, avg_latency=350.0)

    report = isolated_regression_detector.compare_runs(current_run=current_run, previous_run=baseline_run)

    assert report.has_comparison is True
    assert report.latency_increased is True
    assert report.latency_delta_ms == 200.0
    assert "LATENCY REGRESSION DETECTED" in report.status_summary


def test_regression_detection_stable_run(isolated_regression_detector):
    """
    Validates that identical or improved runs show no regressions.
    """
    baseline_run = make_sample_run("run_baseline", pass_rate=100.0, avg_latency=150.0)
    current_run = make_sample_run("run_current", pass_rate=100.0, avg_latency=152.0)

    report = isolated_regression_detector.compare_runs(current_run=current_run, previous_run=baseline_run)

    assert report.has_comparison is True
    assert report.quality_degraded is False
    assert report.latency_increased is False
    assert len(report.newly_failing_tests) == 0
    assert "Quality stable" in report.status_summary


@pytest.mark.asyncio
async def test_end_to_end_test_runner_and_regression(isolated_runner, isolated_regression_detector):
    """
    Validates full automated test suite execution and subsequent regression comparison.
    """
    # Run first execution (baseline)
    run1 = await isolated_runner.run_suite(test_ids=["TC-001", "TC-002", "TC-003"])
    assert run1.total_tests == 3
    assert run1.passed_tests >= 2

    # Run second execution
    run2 = await isolated_runner.run_suite(test_ids=["TC-001", "TC-002", "TC-003"])
    assert run2.total_tests == 3

    # Compare
    report = isolated_regression_detector.compare_runs(current_run=run2, previous_run=run1)
    assert report.has_comparison is True
    assert report.current_run_id == run2.run_id
    assert report.previous_run_id == run1.run_id

