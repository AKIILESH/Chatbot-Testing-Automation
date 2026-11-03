import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import (
    ChatRequest,
    ChatResponse,
    PurchaseRequisitionItem,
    PurchaseOrderItem,
    TestSuiteRun,
    RunTestsRequest,
    HealthResponse,
)
from app.procurement_data import procurement_store
from app.chatbot import ProcurementChatbot
from app.test_runner import TestRunner

app = FastAPI(
    title="ProcureQA API — Groq-Powered Procurement Assistant & QA Testing Framework",
    description="Production-style API for enterprise procurement chat and automated LLM quality evaluation powered by Groq.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

chatbot = ProcurementChatbot()
runner = TestRunner(chatbot=chatbot)


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """
    Check application health, Groq LLM integration status, and test case availability.
    """
    total_cases = len(procurement_store.test_cases)
    return HealthResponse(
        status="healthy",
        app_name="ProcureQA",
        version="2.0.0",
        groq_configured=chatbot.groq_service.is_configured,
        groq_model=chatbot.groq_service.model,
        total_golden_test_cases=total_cases,
        deepeval_installed=runner.evaluator.has_deepeval,
        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    )


@app.post("/chat", response_model=ChatResponse, tags=["Chatbot"])
async def chat(request: ChatRequest):
    """
    Send a procurement question to the Groq-powered chatbot and receive an LLM-generated answer.
    """
    if not request.message or not request.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User query message cannot be empty or whitespace.",
        )

    try:
        response_text, latency_ms, sources = await chatbot.answer_query(prompt=request.message)
        return ChatResponse(
            response=response_text,
            latency_ms=latency_ms,
            sources_consulted=sources,
            model=chatbot.model,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat processing failed: {str(e)}",
        )


@app.get("/requisitions", response_model=List[PurchaseRequisitionItem], tags=["Procurement Data"])
@app.get("/procurement/requisitions", response_model=List[PurchaseRequisitionItem], tags=["Procurement Data"], include_in_schema=False)
async def get_requisitions(status_filter: Optional[str] = Query(None, description="Optional status filter")):
    """
    Retrieve mock purchase requisition records.
    """
    prs = procurement_store.purchase_requisitions
    if status_filter:
        prs = [pr for pr in prs if pr.get("status", "").lower() == status_filter.lower()]
    return prs


@app.get("/purchase-orders", response_model=List[PurchaseOrderItem], tags=["Procurement Data"])
@app.get("/procurement/orders", response_model=List[PurchaseOrderItem], tags=["Procurement Data"], include_in_schema=False)
async def get_purchase_orders(vendor_filter: Optional[str] = Query(None, description="Optional vendor name filter")):
    """
    Retrieve mock purchase orders.
    """
    pos = procurement_store.purchase_orders
    if vendor_filter:
        v_low = vendor_filter.lower()
        pos = [po for po in pos if v_low in po.get("vendor_name", "").lower()]
    return pos


@app.post("/run-tests", response_model=TestSuiteRun, status_code=status.HTTP_201_CREATED, tags=["Test Automation"])
async def run_tests(payload: Optional[RunTestsRequest] = None):
    """
    Execute the automated quality test suite across correctness, hallucination, security, and performance.
    """
    req = payload or RunTestsRequest()
    try:
        suite_run = await runner.run_suite(
            categories=req.categories,
            test_ids=req.test_ids,
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


@app.get("/results", response_model=List[TestSuiteRun], tags=["Test Automation"])
async def get_results():
    """
    Return all historical and latest test results.
    """
    return runner.list_all_runs()


@app.get("/results/{run_id}", response_model=TestSuiteRun, tags=["Test Automation"])
async def get_result_by_id(run_id: str):
    """
    Return detailed results for a specific test run ID.
    """
    run = runner.get_run_by_id(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test run with ID '{run_id}' not found.",
        )
    return run


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=True)
