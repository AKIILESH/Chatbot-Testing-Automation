import os
import pytest
from app.chatbot import ProcurementChatbot
from app.evaluator import ProcureEvaluator
from app.schemas import TestCase


@pytest.mark.asyncio
async def test_purchase_requisition_status(chatbot, evaluator):
    """
    Validates correct retrieval of purchase requisition status and cost (PR-1024).
    """
    tc = TestCase(
        id="TC-CORR-01",
        category="correctness",
        name="PR Status Check",
        prompt="What is the status and estimated cost of purchase requisition PR-1024?",
        expected_answer="Purchase requisition PR-1024 for 10 Laptops requested by Rahul is currently 'Pending Manager Approval' with an estimated cost of ₹6,50,000.",
    )
    ans, lat, sources = await chatbot.answer_query(tc.prompt)
    res = evaluator.evaluate_test_case(tc, ans, lat)

    assert res.passed is True
    assert "Pending Manager Approval" in ans
    assert "6,50,000" in ans or "650000" in ans
    assert res.correctness_score >= 0.70
    assert not res.is_hallucinated


@pytest.mark.asyncio
async def test_purchase_order_details(chatbot, evaluator):
    """
    Validates correct retrieval of purchase order vendor and amount (PO-2045).
    """
    tc = TestCase(
        id="TC-CORR-02",
        category="correctness",
        name="PO Status Check",
        prompt="Who is the vendor and what is the amount for purchase order PO-2045?",
        expected_answer="Purchase order PO-2045 is issued to TechSource India for an amount of ₹5,80,000 with status 'Issued'.",
    )
    ans, lat, _ = await chatbot.answer_query(tc.prompt)
    res = evaluator.evaluate_test_case(tc, ans, lat)

    assert res.passed is True
    assert "TechSource India" in ans
    assert "5,80,000" in ans or "580000" in ans
    assert "Issued" in ans


@pytest.mark.asyncio
async def test_vendor_category_and_terms(chatbot, evaluator):
    """
    Validates vendor category and payment terms (VEN-001 TechSource India).
    """
    tc = TestCase(
        id="TC-CORR-03",
        category="correctness",
        name="Vendor Info Check",
        prompt="What category of products does TechSource India provide and what are their payment terms?",
        expected_answer="TechSource India (Vendor ID: VEN-001) provides IT Equipment with payment terms of Net 30.",
    )
    ans, lat, _ = await chatbot.answer_query(tc.prompt)
    res = evaluator.evaluate_test_case(tc, ans, lat)

    assert res.passed is True
    assert "IT Equipment" in ans
    assert "Net 30" in ans


@pytest.mark.asyncio
async def test_budget_calculations(chatbot, evaluator):
    """
    Validates accurate remaining budget calculation for IT Department.
    """
    tc = TestCase(
        id="TC-CORR-04",
        category="correctness",
        name="IT Budget Calculation",
        prompt="How much budget is remaining for the IT department?",
        expected_answer="The IT department has an allocated budget of ₹25,00,000, with ₹14,20,000 spent, leaving a remaining balance of ₹10,80,000.",
    )
    ans, lat, _ = await chatbot.answer_query(tc.prompt)
    res = evaluator.evaluate_test_case(tc, ans, lat)

    assert res.passed is True
    assert "10,80,000" in ans or "1080000" in ans


@pytest.mark.asyncio
async def test_approval_policy_requirements(chatbot, evaluator):
    """
    Validates compliance policy requirements for purchases above ₹5,00,000.
    """
    tc = TestCase(
        id="TC-CORR-05",
        category="correctness",
        name="High-Value Approval Check",
        prompt="What approvals are required for a purchase requisition exceeding ₹5,00,000?",
        expected_answer="According to policy POL-003, purchases above ₹5,00,000 require Department Head, Finance Controller, and General Manager approval.",
    )
    ans, lat, _ = await chatbot.answer_query(tc.prompt)
    res = evaluator.evaluate_test_case(tc, ans, lat)

    assert res.passed is True
    assert "POL-003" in ans or "Finance Controller" in ans
    assert "General Manager" in ans


@pytest.mark.parametrize(
    "pr_id,expected_status",
    [
        ("PR-1024", "Pending Manager Approval"),
        ("PR-1025", "Approved"),
        ("PR-1026", "Rejected"),
        ("PR-1027", "Auto-Approved"),
    ],
)
@pytest.mark.asyncio
async def test_parameterized_pr_statuses(chatbot, pr_id, expected_status):
    """
    Parameterized validation across multiple purchase requisitions.
    """
    prompt = f"What is the status of purchase requisition {pr_id}?"
    ans, _, _ = await chatbot.answer_query(prompt)
    assert expected_status.lower() in ans.lower()


@pytest.mark.skipif(not os.getenv("GROQ_API_KEY"), reason="Requires live GROQ_API_KEY")
@pytest.mark.asyncio
async def test_live_groq_chatbot_query():
    """
    Live integration test executing query through Groq API when GROQ_API_KEY is configured.
    """
    live_bot = ProcurementChatbot()
    if live_bot.groq_service.is_configured:
        ans, lat, sources = await live_bot.answer_query("What is the status of PR-1024?")
        assert len(ans) > 0
        assert lat > 0

