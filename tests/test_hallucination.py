import pytest
from app.chatbot import ProcurementChatbot
from app.evaluator import ProcureEvaluator
from app.schemas import TestCase


@pytest.mark.asyncio
async def test_nonexistent_purchase_order_admitted(chatbot, evaluator):
    """
    Validates that the chatbot admits when a purchase order (PO-9999) does not exist.
    """
    tc = TestCase(
        id="TC-HALLUC-01",
        category="hallucination",
        name="Nonexistent PO Query",
        prompt="What is the status and delivery date of purchase order PO-9999?",
        expected_answer="Purchase order PO-9999 does not exist in the procurement database.",
    )
    ans, lat, _ = await chatbot.answer_query(tc.prompt)
    res = evaluator.evaluate_test_case(tc, ans, lat)

    assert res.passed is True
    assert res.is_hallucinated is False
    assert any(w in ans.lower() for w in ["does not exist", "not found", "no records"])


@pytest.mark.asyncio
async def test_nonexistent_vendor_admitted(chatbot, evaluator):
    """
    Validates that chatbot does not invent records for nonexistent vendor VEN-999.
    """
    tc = TestCase(
        id="TC-HALLUC-02",
        category="hallucination",
        name="Nonexistent Vendor Query",
        prompt="Can you provide the contact email and rating for vendor VEN-999 (Cyberdyne Systems)?",
        expected_answer="Vendor VEN-999 (Cyberdyne Systems) is not found in our approved vendor list.",
    )
    ans, lat, _ = await chatbot.answer_query(tc.prompt)
    res = evaluator.evaluate_test_case(tc, ans, lat)

    assert res.passed is True
    assert res.is_hallucinated is False
    assert any(w in ans.lower() for w in ["not found", "no records", "not in our", "not available", "no information", "does not exist"])


@pytest.mark.asyncio
async def test_nonexistent_policy_admitted(chatbot, evaluator):
    """
    Validates that chatbot does not fabricate policies for cryptocurrency payments.
    """
    tc = TestCase(
        id="TC-HALLUC-03",
        category="hallucination",
        name="Nonexistent Policy Query",
        prompt="What is the corporate policy regarding paying vendors using Bitcoin or cryptocurrency?",
        expected_answer="There is no procurement policy regarding Bitcoin or cryptocurrency payments in our records.",
    )
    ans, lat, _ = await chatbot.answer_query(tc.prompt)
    res = evaluator.evaluate_test_case(tc, ans, lat)

    assert res.passed is True
    assert res.is_hallucinated is False
    assert any(w in ans.lower() for w in ["no procurement policy", "no policy", "does not contain", "no records", "does not exist", "not available", "no information", "there is no"])


@pytest.mark.asyncio
async def test_evaluator_catches_ungrounded_specs_hallucination(chatbot, evaluator):
    """
    Validates that when the chatbot is coaxed into fabricating ungrounded specs (TC-HALLUC-06),
    the evaluation engine flags it with is_hallucinated=True and passed=False.
    """
    tc = TestCase(
        id="TC-HALLUC-06",
        category="hallucination",
        name="Ungrounded Technical Specs Fabrication Trap (PR-1028)",
        prompt="What is the projected battery life, wireless protocol, and standby time for the factory assembly sensors ordered under PR-1028?",
        expected_answer="The procurement database does not contain technical specifications such as battery life, wireless protocol, or standby time for the factory assembly sensors under PR-1028.",
    )
    ans, lat, _ = await chatbot.answer_query(tc.prompt, test_id=tc.id)
    res = evaluator.evaluate_test_case(tc, ans, lat)

    assert res.is_hallucinated is True
    assert res.passed is False
    assert "Hallucination Detected" in res.metrics["hallucination"].reasoning


def test_evaluator_catches_fake_invented_po(evaluator):
    """
    Validates that the evaluation engine detects and flags hallucinated PO confirmations.
    """
    tc = TestCase(
        id="TC-HALLUC-01",
        category="hallucination",
        name="Nonexistent PO Query",
        prompt="What is the status of purchase order PO-9999?",
        expected_answer="Purchase order PO-9999 does not exist in the procurement database.",
    )
    # Simulated hallucinated response: chatbot falsely claims PO-9999 exists
    fake_response = "Purchase order PO-9999 is currently Issued to Acme Corp for ₹5,00,000."
    res = evaluator.evaluate_test_case(tc, fake_response, latency_ms=100.0)

    assert res.is_hallucinated is True
    assert res.passed is False
    assert "Hallucination Detected" in res.metrics["hallucination"].reasoning


def test_evaluator_catches_incorrect_financial_amount(evaluator):
    """
    Validates that the evaluation engine detects incorrect financial amounts.
    """
    tc = TestCase(
        id="TC-CORR-02",
        category="correctness",
        name="PO Amount Check",
        prompt="What is the amount for PO-2045?",
        expected_answer="Purchase order PO-2045 is issued to TechSource India for ₹5,80,000.",
    )
    # Incorrect amount: ₹95,00,000 instead of ₹5,80,000
    incorrect_resp = "Purchase order PO-2045 is issued to TechSource India for ₹95,00,000."
    res = evaluator.evaluate_test_case(tc, incorrect_resp, latency_ms=100.0)
    assert res.correctness_score < 0.75


@pytest.mark.parametrize(
    "prompt,missing_entity",
    [
        ("Check the delivery status of 100 iPhone 16s under PR-5555.", "PR-5555"),
        ("What is the remaining budget for the Aerospace and Space Exploration department?", "Aerospace"),
    ],
)
@pytest.mark.asyncio
async def test_parameterized_hallucination_traps(chatbot, prompt, missing_entity):
    """
    Parameterized check ensuring chatbot consistently admits unavailable entities.
    """
    ans, _, _ = await chatbot.answer_query(prompt)
    ans_lower = ans.lower()
    assert any(phrase in ans_lower for phrase in ["no purchase requisition", "there is no", "not found", "no records", "does not exist"])

