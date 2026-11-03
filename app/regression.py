from typing import Optional, List, Dict, Any
from app.schemas import TestSuiteRun, RegressionReport
from app.test_runner import TestRunner


class RegressionDetector:
    """
    Automated Regression Testing Engine for LLMs.
    Detects quality degradation, newly failing test cases, and latency regressions
    between baseline/previous and current test suite runs.
    """

    def __init__(self, test_runner: Optional[TestRunner] = None):
        self.runner = test_runner or TestRunner()

    def compare_runs(
        self,
        current_run: TestSuiteRun,
        previous_run: Optional[TestSuiteRun] = None,
        latency_tolerance_pct: float = 20.0,
        pass_rate_tolerance_pct: float = 0.0,
    ) -> RegressionReport:
        """
        Compares current test execution with previous/baseline run.
        """
        if not previous_run:
            # Try to fetch historical runs from disk
            history = self.runner.list_all_runs()
            # History is sorted newest to oldest; find the run preceding current_run
            for r in history:
                if r.run_id != current_run.run_id:
                    previous_run = r
                    break

        if not previous_run:
            return RegressionReport(
                has_comparison=False,
                current_run_id=current_run.run_id,
                current_pass_rate=current_run.pass_rate,
                current_avg_latency_ms=current_run.avg_latency_ms,
                status_summary="Baseline run established. No previous run found for regression comparison.",
            )

        # Map results by test_id for fast comparison
        curr_map = {res.test_id: res for res in current_run.results}
        prev_map = {res.test_id: res for res in previous_run.results}

        newly_failing: List[str] = []
        newly_passing: List[str] = []

        for test_id, curr_res in curr_map.items():
            prev_res = prev_map.get(test_id)
            if prev_res:
                if prev_res.passed and not curr_res.passed:
                    newly_failing.append(f"{test_id}: {curr_res.name}")
                elif not prev_res.passed and curr_res.passed:
                    newly_passing.append(f"{test_id}: {curr_res.name}")

        pass_rate_delta = round(current_run.pass_rate - previous_run.pass_rate, 2)
        latency_delta = round(current_run.avg_latency_ms - previous_run.avg_latency_ms, 2)

        # Degradation conditions
        quality_degraded = (
            (pass_rate_delta < -pass_rate_tolerance_pct)
            or (len(newly_failing) > 0)
            or (current_run.hallucination_rate > previous_run.hallucination_rate)
        )

        latency_increased = False
        if previous_run.avg_latency_ms > 0:
            pct_change = (latency_delta / previous_run.avg_latency_ms) * 100.0
            if pct_change > latency_tolerance_pct and latency_delta > 100:
                latency_increased = True

        # Generate summary message
        summary_parts = []
        if quality_degraded:
            summary_parts.append(
                f"QUALITY REGRESSION DETECTED: Pass rate shifted from {previous_run.pass_rate}% to {current_run.pass_rate}% "
                f"({pass_rate_delta:+0.2f}%). {len(newly_failing)} previously passing tests failed."
            )
        else:
            summary_parts.append(
                f"Quality stable: Pass rate {current_run.pass_rate}% (Delta: {pass_rate_delta:+0.2f}%)."
            )

        if latency_increased:
            summary_parts.append(
                f"LATENCY REGRESSION DETECTED: Average response latency increased by {latency_delta:+0.1f}ms."
            )
        else:
            summary_parts.append(
                f"Latency stable: {current_run.avg_latency_ms}ms (Delta: {latency_delta:+0.1f}ms)."
            )

        return RegressionReport(
            has_comparison=True,
            current_run_id=current_run.run_id,
            previous_run_id=previous_run.run_id,
            current_pass_rate=current_run.pass_rate,
            previous_pass_rate=previous_run.pass_rate,
            pass_rate_delta=pass_rate_delta,
            current_avg_latency_ms=current_run.avg_latency_ms,
            previous_avg_latency_ms=previous_run.avg_latency_ms,
            latency_delta_ms=latency_delta,
            quality_degraded=quality_degraded,
            latency_increased=latency_increased,
            newly_failing_tests=newly_failing,
            newly_passing_tests=newly_passing,
            status_summary=" | ".join(summary_parts),
        )

    def evaluate_latest_regression(self) -> RegressionReport:
        """
        Loads the two most recent runs and compares them.
        """
        history = self.runner.list_all_runs()
        if not history:
            return RegressionReport(
                has_comparison=False,
                current_run_id="none",
                current_pass_rate=0.0,
                current_avg_latency_ms=0.0,
                status_summary="No test execution records found in storage.",
            )

        if len(history) == 1:
            return RegressionReport(
                has_comparison=False,
                current_run_id=history[0].run_id,
                current_pass_rate=history[0].pass_rate,
                current_avg_latency_ms=history[0].avg_latency_ms,
                status_summary="Only 1 run found. Execute another test run to detect regressions.",
            )

        return self.compare_runs(current_run=history[0], previous_run=history[1])
