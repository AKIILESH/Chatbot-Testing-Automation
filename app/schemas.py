from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., description="Role: user or assistant")
    content: str = Field(..., description="Message text")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User query directed to the procurement chatbot")
    history: Optional[List[ChatMessage]] = Field(default=None, description="Optional conversational history")


class ChatResponse(BaseModel):
    response: str
    latency_ms: float
    sources_consulted: List[str] = Field(default_factory=list)
    model: str = "llama-3.3-70b-versatile"


class PurchaseRequisitionItem(BaseModel):
    id: str
    requester: str
    department: str
    item: str
    status: str
    estimated_cost: float
    rejection_reason: Optional[str] = None
    date: str


class PurchaseOrderItem(BaseModel):
    id: str
    vendor_id: str
    vendor_name: str
    amount: float
    status: str
    pr_id: str
    delivery_date: str
    items: str


class TestCase(BaseModel):
    __test__ = False
    id: str = Field(..., description="Unique test case identifier")
    category: str = Field(..., description="correctness, hallucination, security, api_testing, performance")
    name: str = Field(..., description="Scenario name")
    prompt: str = Field(..., description="User query/test prompt")
    context: Optional[str] = Field(None, description="Optional grounding context")
    expected_answer: str = Field(..., description="Expected factual answer or security refusal")
    security_sensitive: bool = Field(False, description="Whether test probes security/jailbreaks")
    max_allowed_latency_ms: float = Field(2500.0, description="Latency SLA in milliseconds")


class MetricScore(BaseModel):
    score: float = Field(..., ge=0.0, le=1.0)
    threshold: float = Field(..., ge=0.0, le=1.0)
    passed: bool
    reasoning: str
    evaluator: str = "deterministic"


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
    security_sensitive: bool = False
    security_incident_detected: bool = False
    correctness_score: float = Field(0.0, ge=0.0, le=1.0)
    faithfulness_score: float = Field(0.0, ge=0.0, le=1.0)
    relevance_score: float = Field(0.0, ge=0.0, le=1.0)
    hallucination_score: float = Field(0.0, ge=0.0, le=1.0)
    metrics: Dict[str, MetricScore] = Field(default_factory=dict)
    error: Optional[str] = None


class TestSuiteRun(BaseModel):
    __test__ = False
    run_id: str
    timestamp: str
    model_name: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    pass_rate: float
    avg_latency_ms: float
    hallucination_rate: float
    results: List[TestResult]


class RunTestsRequest(BaseModel):
    model: Optional[str] = None
    categories: Optional[List[str]] = None
    test_ids: Optional[List[str]] = None


class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str
    groq_configured: bool = False
    groq_model: str = ""
    total_golden_test_cases: int
    deepeval_installed: bool
    timestamp: str
