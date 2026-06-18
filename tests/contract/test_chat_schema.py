from app.models.chat import ChatResponse


def test_chat_contract_has_frontend_fields():
    data = ChatResponse(chat_id="c1", response="ok").model_dump()
    assert {"chat_id", "response", "quiz_data"} <= data.keys()
