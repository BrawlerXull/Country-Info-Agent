"""
Shared pytest fixtures for the Country Info Agent test suite.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import os

# Set test environment variables before importing app modules
os.environ.setdefault("OPENAI_API_KEY", "test-api-key")
os.environ.setdefault("GOOGLE_API_KEY", "test-google-key")


@pytest.fixture
def mock_country_data():
    """Sample country data from REST Countries API."""
    return {
        "name": {
            "common": "Germany",
            "official": "Federal Republic of Germany"
        },
        "capital": ["Berlin"],
        "population": 83240525,
        "currencies": {
            "EUR": {"name": "Euro", "symbol": "€"}
        },
        "languages": {"deu": "German"},
        "flags": {
            "png": "https://flagcdn.com/w320/de.png",
            "svg": "https://flagcdn.com/de.svg"
        },
        "region": "Europe",
        "subregion": "Western Europe"
    }


@pytest.fixture
def mock_india_data():
    """Sample India country data."""
    return {
        "name": {
            "common": "India",
            "official": "Republic of India"
        },
        "capital": ["New Delhi"],
        "population": 1380004385,
        "currencies": {
            "INR": {"name": "Indian rupee", "symbol": "₹"}
        },
        "languages": {"eng": "English", "hin": "Hindi"},
        "flags": {
            "png": "https://flagcdn.com/w320/in.png"
        },
        "region": "Asia",
        "subregion": "Southern Asia"
    }


@pytest.fixture
def mock_httpx_response(mock_country_data):
    """Mock httpx response for country API."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [mock_country_data]
    return mock_response


@pytest.fixture
def mock_agent_state():
    """Base agent state for testing nodes."""
    return {
        "question": "What is the population of Germany?",
        "messages": [],
        "intent": None,
        "countries": None,
        "tool_outputs": None,
        "final_answer": None,
        "error": None
    }


@pytest.fixture
def mock_runnable_config():
    """Mock RunnableConfig for node testing."""
    return {"configurable": {"thread_id": "test-session"}}
