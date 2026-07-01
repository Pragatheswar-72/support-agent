import pytest

from src import tools
from src.backend.db import get_engine, get_session_factory
from src.backend.seed import seed


@pytest.fixture(autouse=True)
def seeded_db():
    engine = get_engine("sqlite:///:memory:")
    tools.configure_db(engine)
    session = get_session_factory(engine)()
    seed(session)
    yield


def test_get_order_status_found():
    assert tools.get_order_status(1001) == {"order_id": 1001, "status": "delivered"}


def test_get_order_status_not_found():
    result = tools.get_order_status(9999)
    assert "error" in result


def test_get_order_details():
    result = tools.get_order_details(1002)
    assert result["customer_name"] == "Ben Torres"
    assert result["status"] == "shipped"


def test_track_shipment_delivered():
    result = tools.track_shipment(1001)
    assert result["tracking_message"] == "Delivered."


def test_refund_eligibility_delivered_no_existing_refund():
    result = tools.check_refund_eligibility(1001)
    assert result["eligible"] is True


def test_refund_eligibility_not_delivered():
    result = tools.check_refund_eligibility(1002)  # shipped
    assert result["eligible"] is False
    assert "delivered" in result["reason"]


def test_refund_eligibility_already_requested():
    result = tools.check_refund_eligibility(1004)  # delivered but refund already requested
    assert result["eligible"] is False
    assert "already" in result["reason"]


def test_initiate_refund_succeeds_when_eligible():
    result = tools.initiate_refund(1001, "Item not as described")
    assert result["success"] is True
    assert result["status"] == "requested"
    # DB actually changed
    assert tools.check_refund_eligibility(1001)["eligible"] is False


def test_initiate_refund_refuses_when_not_delivered():
    result = tools.initiate_refund(1002, "Changed my mind")
    assert result["success"] is False
    assert "delivered" in result["reason"]


def test_get_payment_status():
    result = tools.get_payment_status(1003)
    assert result["status"] == "pending"


def test_process_payment_succeeds_when_pending():
    result = tools.process_payment(1003, "paypal")
    assert result["success"] is True
    assert tools.get_payment_status(1003)["status"] == "paid"


def test_process_payment_refuses_when_already_paid():
    result = tools.process_payment(1001, "card")
    assert result["success"] is False


def test_answer_faq_shipping():
    answer = tools.answer_faq("How long does shipping take?")
    assert "3-5 business days" in answer


def test_answer_faq_fallback():
    answer = tools.answer_faq("What is the meaning of life?")
    assert "support@example.com" in answer


def test_escalate_to_human():
    result = tools.escalate_to_human("agent could not resolve", "user asked about order 9999")
    assert result["escalated"] is True
    assert "ticket_id" in result
