import pytest
from unittest.mock import MagicMock, patch
from app.nodes import identify_intent, invoke_tool, synthesize_answer
from app.state import AgentState

@pytest.fixture
def mock_llm():
    with patch("app.nodes.get_llm") as mock:
        yield mock

@pytest.fixture
def mock_fetch_country():
    with patch("app.nodes.fetch_country_info") as mock:
        yield mock

def test_invoke_tool_success(mock_fetch_country):
    mock_fetch_country.return_value = {"status": "success", "data": {"population": 1000}}
    state = {"country": "Germany", "intent": "get_population", "question": "Pop of Germany?"}
    
    result = invoke_tool(state)
    assert result["tool_output"]["status"] == "success"
    assert result["tool_output"]["data"]["population"] == 1000

def test_invoke_tool_no_country():
    state = {"country": None, "intent": "unknown", "question": "Hello"}
    result = invoke_tool(state)
    assert result["tool_output"] is None

def test_synthesize_answer_error(mock_llm):
    state = {
        "question": "TEST",
        "tool_output": {"status": "error", "message": "Not found"},
        "intent": "get_population"
    }
    result = synthesize_answer(state)
    assert "error" in result["final_answer"]

def test_synthesize_answer_no_data(mock_llm):
    state = {
        "question": "TEST",
        "tool_output": None,  # e.g. from unknown intent but passed vaguely
        "intent": "get_population"  # Weird state but possible
    }
    # If tool output is None but intent was valid (maybe empty tool result?), 
    # the code currently handles `not tool_output` -> "couldn't find information"
    result = synthesize_answer(state)
    assert "couldn't find" in result["final_answer"]

# Note: Testing identify_intent logic requires mocking the chain.invoke or the LLM response more deeply.
# For simplicity in this assignment, we focus on the logic flow.
