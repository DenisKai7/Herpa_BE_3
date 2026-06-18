import pytest
from app.agents.safety_agent import SafetyAgent


@pytest.mark.asyncio
async def test_detects_emergency_phrase():
    state = {"user_query": "Saya mengalami nyeri dada sejak pagi"}
    result = await SafetyAgent().run(state)
    assert result["red_flags"]


@pytest.mark.asyncio
async def test_does_not_match_substring():
    state = {"user_query": "Saya sedang belajar tentang dadaisme"}
    result = await SafetyAgent().run(state)
    assert result["red_flags"] == []
