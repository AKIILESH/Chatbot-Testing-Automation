import os
import json
import uuid
import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from app.schemas import TestCase, TestResult, TestSuiteRun
from app.llm_client import LLMClient
from app.evaluator import QualityEvaluator


class TestRunner:
    """
    Automated Test Runner for LLM Quality & Safety Evaluation.
    Loads golden datasets, executes test suites, records latencies, evaluates results,
    and persists structured audit reports.
    """

    def __init__(
        self,
        dataset_path: Optional[str] = None,
        reports_dir: Optional[str] = None,
        llm_client: Optional[LLMClient] = None,
        evaluator: Optional[QualityEvaluator] = None,
    ):
        base_dir = Path(__file__).resolve().parent.parent
        self.dataset_path = Path(dataset_path or (base_dir / "data" / "golden_dataset.json"))
        self.reports_dir = Path(reports_dir or (base_dir / "reports"))
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        self.llm_client = llm_client or LLMClient()
        self.evaluator = evaluator or QualityEvaluator()

    def load_test_cases(
        self,
        categories: Optional[List[str]] = None,
        test_ids: Optional[List[str]] = None,
    ) -> List[TestCase]:
        """
        Loads test cases from the golden dataset with optional filtering.
        """
        if not self.dataset_path.exists():
            raise FileNotFoundError(f"Golden dataset not found at {self.dataset_path}")

        with open(self.dataset_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        raw_cases = data.get("test_cases", [])
        test_cases: List[TestCase] = []

        for item in raw_cases:
            if test_ids and item.get("id") not in test_ids:
                continue
            if categories and item.get("category") not in categories:
                continue
            test_cases.append(TestCase(**item))

        return test_cases

    async def run_suite(
        self,
        test_cases: Optional[List[TestCase]] = None,
        categories: Optional[List[str]] = None,
        test_ids: Optional[List[str]] = None,
        use_mock: Optional[bool] = None,
        model: Optional[str] = None,
        simulate_flaws: bool = False,
    ) -> TestSuiteRun:
        """
        Executes test suite asynchronously, calculates aggregate QA metrics,
        and saves execution report.
        """
        if use_mock is not None or model is not None:
            self.llm_client = LLMClient(use_mock=use_mock, model=model)

        cases_to_run = test_cases or self.load_test_cases(categories=categories, test_ids=test_ids)
        if not cases_to_run:
            raise ValueError("No test cases selected for execution.")

        run_id = f"run_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

        results: List[TestResult] = []

        for tc in cases_to_run:
            try:
                actual_response, latency_ms = await self.llm_client.generate_response(
                    prompt=tc.prompt,
                    context=tc.context,
                    test_id=tc.id,
                    simulate_flaws=simulate_flaws,
                )

                result = self.evaluator.evaluate_test_case(
                    test_case=tc,
                    actual_response=actual_response,
                    latency_ms=latency_ms,
                )
            except Exception as e:
                # Capture test failure gracefully
                result = TestResult(
                    test_id=tc.id,
                    name=tc.name,
                    category=tc.category,
                    prompt=tc.prompt,
                    context=tc.context,
                    expected_answer=tc.expected_answer,
                    actual_response="",
                    latency_ms=0.0,
                    passed=False,
                    is_hallucinated=False,
                    security_sensitive=tc.security_sensitive,
                    error=f"Execution error: {str(e)}",
                )

            results.append(result)

        # Aggregate metrics
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed
        pass_rate = round((passed / total) * 100.0, 2) if total > 0 else 0.0

        latencies = [r.latency_ms for r in results if r.latency_ms > 0]
        avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0.0

        hallucinated_count = sum(1 for r in results if r.is_hallucinated)
        hallucination_rate = round((hallucinated_count / total) * 100.0, 2) if total > 0 else 0.0

        suite_run = TestSuiteRun(
            run_id=run_id,
            timestamp=timestamp,
            model_name=self.llm_client.model,
            is_mock=self.llm_client.use_mock,
            total_tests=total,
            passed_tests=passed,
            failed_tests=failed,
            pass_rate=pass_rate,
            avg_latency_ms=avg_latency,
            hallucination_rate=hallucination_rate,
            results=results,
        )

        # Persist report
        self.save_report(suite_run)

        return suite_run

    def save_report(self, run: TestSuiteRun) -> Path:
        """
        Saves run report to both timestamped file and latest.json.
        """
        report_file = self.reports_dir / f"{run.run_id}.json"
        latest_file = self.reports_dir / "latest.json"

        data = run.model_dump()
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        with open(latest_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        return report_file

    def get_run_by_id(self, run_id: str) -> Optional[TestSuiteRun]:
        """
        Retrieves a specific test run by its run_id.
        """
        report_file = self.reports_dir / f"{run_id}.json"
        if not report_file.exists():
            return None
        with open(report_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return TestSuiteRun(**data)

    def get_latest_run(self) -> Optional[TestSuiteRun]:
        """
        Retrieves the most recent test run.
        """
        latest_file = self.reports_dir / "latest.json"
        if latest_file.exists():
            with open(latest_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return TestSuiteRun(**data)

        history = self.list_all_runs()
        return history[0] if history else None

    def list_all_runs(self) -> List[TestSuiteRun]:
        """
        Returns all historical test runs sorted from newest to oldest.
        """
        runs: List[TestSuiteRun] = []
        for file in sorted(self.reports_dir.glob("run_*.json"), reverse=True):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                runs.append(TestSuiteRun(**data))
            except Exception:
                continue
        return runs

