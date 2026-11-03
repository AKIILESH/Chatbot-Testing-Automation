import os
import json
import uuid
import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from app.schemas import TestCase, TestResult, TestSuiteRun
from app.chatbot import ProcurementChatbot
from app.evaluator import ProcureEvaluator
from app.procurement_data import procurement_store


class TestRunner:
    """
    Automated Test Runner for Procurement Chatbot powered by Groq.
    Loads procurement golden test cases, triggers chatbot, executes evaluations,
    and stores structured audit reports.
    """

    def __init__(
        self,
        reports_dir: Optional[str] = None,
        chatbot: Optional[ProcurementChatbot] = None,
        evaluator: Optional[ProcureEvaluator] = None,
    ):
        base_dir = Path(__file__).resolve().parent.parent
        self.reports_dir = Path(reports_dir or (base_dir / "reports"))
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        self.chatbot = chatbot or ProcurementChatbot()
        self.evaluator = evaluator or ProcureEvaluator()

    def load_test_cases(
        self,
        categories: Optional[List[str]] = None,
        test_ids: Optional[List[str]] = None,
    ) -> List[TestCase]:
        raw_cases = procurement_store.test_cases
        cases: List[TestCase] = []

        for item in raw_cases:
            if test_ids and item.get("id") not in test_ids:
                continue
            if categories and item.get("category") not in categories:
                continue
            cases.append(TestCase(**item))

        return cases

    async def run_suite(
        self,
        test_cases: Optional[List[TestCase]] = None,
        categories: Optional[List[str]] = None,
        test_ids: Optional[List[str]] = None,
        model: Optional[str] = None,
        simulate_flaw: bool = False,
    ) -> TestSuiteRun:
        if model is not None:
            self.chatbot = ProcurementChatbot(model=model)

        cases_to_run = test_cases or self.load_test_cases(categories=categories, test_ids=test_ids)
        if not cases_to_run:
            raise ValueError("No test cases selected for execution.")

        run_id = f"procure_run_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        results: List[TestResult] = []

        for tc in cases_to_run:
            try:
                actual_response, latency_ms, _ = await self.chatbot.answer_query(
                    prompt=tc.prompt,
                    test_id=tc.id,
                    simulate_flaw=simulate_flaw,
                )
                result = self.evaluator.evaluate_test_case(
                    test_case=tc,
                    actual_response=actual_response,
                    latency_ms=latency_ms,
                )
            except Exception as e:
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
            model_name=self.chatbot.model,
            total_tests=total,
            passed_tests=passed,
            failed_tests=failed,
            pass_rate=pass_rate,
            avg_latency_ms=avg_latency,
            hallucination_rate=hallucination_rate,
            results=results,
        )

        is_partial = bool(categories or test_ids)
        self.save_report(suite_run, is_partial=is_partial)
        return suite_run

    def save_report(self, run: TestSuiteRun, is_partial: bool = False) -> Path:
        report_file = self.reports_dir / f"{run.run_id}.json"
        latest_file = self.reports_dir / "latest.json"

        data = run.model_dump()
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        # Only update latest.json if this is a full suite run (or if latest.json does not exist yet)
        if not is_partial or not latest_file.exists():
            with open(latest_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        return report_file

    def get_run_by_id(self, run_id: str) -> Optional[TestSuiteRun]:
        report_file = self.reports_dir / f"{run_id}.json"
        if not report_file.exists():
            return None
        with open(report_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return TestSuiteRun(**data)

    def get_latest_run(self) -> Optional[TestSuiteRun]:
        latest_file = self.reports_dir / "latest.json"
        if latest_file.exists():
            try:
                with open(latest_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return TestSuiteRun(**data)
            except Exception:
                pass
        history = self.list_all_runs()
        return history[0] if history else None

    def list_all_runs(self) -> List[TestSuiteRun]:
        runs: List[TestSuiteRun] = []
        for file in sorted(self.reports_dir.glob("procure_run_*.json"), reverse=True):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                runs.append(TestSuiteRun(**data))
            except Exception:
                continue
        return runs
