from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class TestCase(BaseModel):
    __test__ = False
    id: str = Field(..., description="Unique test case identifier")
    category: str = Field(..., description="Category: smart_home_factual, general_factual, context_grounded, hallucination_detection, multi_turn_context, security_prompt_injection, security_pii_leakage, security_unauthorized_device_control, refusal_behavior, incorrect_answer_scenario")
    name: str = Field(..., description="Descriptive name of test scenario")
    prompt: str = Field(..., description="Input prompt delivered to LLM")
    context: Optional[str] = Field(None, description="Grounding context or dialogue history")
    expected_answer: str = Field(..., description="Reference golden answer or expected safety refusal")
    security_sensitive: bool = Field(False, description="Whether test represents a security / adversarial boundary")
    max_allowed_latency_ms: float = Field(3000.0, description="Max acceptable latency in milliseconds")


class MetricScore(BaseModel):
    score: float = Field(..., ge=0.0, le=1.0, description="Normalized score 0.0 to 1.0")
    threshold: float = Field(..., ge=0.0, le=1.0, description="Passing threshold")
    passed: bool = Field(..., description="Whether score meets criteria")
    reasoning: str = Field(..., description="Detailed explanation of evaluation determination")
    evaluator: str = Field("hybrid", description="Evaluation engine name (e.g. deepeval, semantic, rule-guard)")


class TestResult(BaseModel):
    __test__ = False
    test_id: str
    name: str
    category: str
    prompt: str
    context: Optional[str] = None
    expected_answer: str
    actual_response: str
    latency_ms: float
    passed: bool
    is_hallucinated: bool
    correctness_score: float = Field(0.0, ge=0.0, le=1.0)
    contextual_relevance_score: float = Field(0.0, ge=0.0, le=1.0)
    faithfulness_score: float = Field(0.0, ge=0.0, le=1.0)
    hallucination_score: float = Field(0.0, ge=0.0, le=1.0)
    metrics: Dict[str, MetricScore] = Field(default_factory=dict)
    security_incident_detected: bool = False
    error: Optional[str] = None


class TestSuiteRun(BaseModel):
    __test__ = False
    run_id: str
    timestamp: str
    model_name: str
    is_mock: bool
    total_tests: int
    passed_tests: int
    failed_tests: int
    pass_rate: float
    avg_latency_ms: float
    hallucination_rate: float
    results: List[TestResult]


class RegressionReport(BaseModel):
    has_comparison: bool
    current_run_id: str
    previous_run_id: Optional[str] = None
    current_pass_rate: float
    previous_pass_rate: Optional[float] = None
    pass_rate_delta: Optional[float] = None
    current_avg_latency_ms: float
    previous_avg_latency_ms: Optional[float] = None
    latency_delta_ms: Optional[float] = None
    quality_degraded: bool = False
    latency_increased: bool = False
    newly_failing_tests: List[str] = Field(default_factory=list)
    newly_passing_tests: List[str] = Field(default_factory=list)
    status_summary: str = "No regression detected"


class RunTestsRequest(BaseModel):
    use_mock: Optional[bool] = None
    model: Optional[str] = None
    categories: Optional[List[str]] = None
    test_ids: Optional[List[str]] = None


class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str
    mock_llm_enabled: bool
    total_golden_test_cases: int
    deepeval_installed: bool
    timestamp: str
