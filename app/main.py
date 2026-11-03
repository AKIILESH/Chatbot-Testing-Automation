import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import (
    TestCase,
    TestSuiteRun,
    RegressionReport,
    RunTestsRequest,
    HealthResponse,
)
from app.test_runner import TestRunner
from app.regression import RegressionDetector

app = FastAPI(
    title="LLM Quality Tester API",
    description="Automated AI Quality Engineering platform for evaluation, security, hallucination detection, and regression testing.",
    version="1.0.0",
)

# Enable CORS for frontend & dashboard interactions
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

runner = TestRunner()
regression_detector = RegressionDetector(test_runner=runner)


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """
    Returns API health status, version, evaluator readiness, and dataset size.
    """
    try:
        cases = runner.load_test_cases()
        total_cases = len(cases)
    except Exception:
        total_cases = 0

    return HealthResponse(
        status="healthy",
        app_name="LLM Quality Tester",
        version="1.0.0",
        mock_llm_enabled=runner.llm_client.use_mock,
        total_golden_test_cases=total_cases,
        deepeval_installed=runner.evaluator.has_deepeval,
        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    )


@app.get("/test-cases", response_model=List[TestCase], tags=["Test Cases"])
async def get_test_cases(
    category: Optional[str] = Query(None, description="Filter test cases by category"),
    security_only: Optional[bool] = Query(None, description="Filter for security-sensitive tests"),
):
    """
    Retrieves test cases from the golden dataset with optional category filtering.
    """
    try:
        categories = [category] if category else None
        cases = runner.load_test_cases(categories=categories)
        if security_only:
            cases = [c for c in cases if c.security_sensitive or "security" in c.category]
        return cases
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load test cases: {str(e)}",
        )


@app.post("/run-tests", response_model=TestSuiteRun, status_code=status.HTTP_201_CREATED, tags=["Execution"])
async def run_tests(payload: Optional[RunTestsRequest] = None):
    """
    Triggers automated test suite execution against LLM.
    Evaluates correctness, latency, security guardrails, and hallucination metrics.
    """
    req = payload or RunTestsRequest()
    try:
        suite_run = await runner.run_suite(
            categories=req.categories,
            test_ids=req.test_ids,
            use_mock=req.use_mock,
            model=req.model,
        )
        return suite_run
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Test run execution failed: {str(e)}",
        )


@app.get("/results", response_model=List[TestSuiteRun], tags=["Reports"])
async def get_all_results():
    """
    Retrieves all historical test execution runs sorted newest to oldest.
    """
    try:
        return runner.list_all_runs()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch test run history: {str(e)}",
        )


@app.get("/results/{run_id}", response_model=TestSuiteRun, tags=["Reports"])
async def get_result_by_id(run_id: str):
    """
    Retrieves detailed results for a specific test run.
    """
    run = runner.get_run_by_id(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test run with ID '{run_id}' not found.",
        )
    return run


@app.get("/regression", response_model=RegressionReport, tags=["Regression"])
async def get_regression_report(
    current_run_id: Optional[str] = Query(None, description="Optional run ID for current evaluation"),
    baseline_run_id: Optional[str] = Query(None, description="Optional run ID for baseline comparison"),
):
    """
    Compares test runs to detect quality degradation, latency regressions,
    and newly failing test cases.
    """
    try:
        if current_run_id and baseline_run_id:
            curr = runner.get_run_by_id(current_run_id)
            base = runner.get_run_by_id(baseline_run_id)
            if not curr:
                raise HTTPException(status_code=404, detail=f"Current run '{current_run_id}' not found.")
            if not base:
                raise HTTPException(status_code=404, detail=f"Baseline run '{baseline_run_id}' not found.")
            return regression_detector.compare_runs(current_run=curr, previous_run=base)

        return regression_detector.evaluate_latest_regression()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Regression evaluation failed: {str(e)}",
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=True)

