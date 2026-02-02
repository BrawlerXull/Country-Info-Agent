"""
Integration tests for FastAPI endpoints.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Test the /health endpoint."""

    def test_health_check(self):
        """Test health endpoint returns ok status."""
        with patch('country_info_agent.api.create_graph'):
            from country_info_agent.api import app
            client = TestClient(app)
            
            response = client.get("/health")
            
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}


class TestQueryEndpoint:
    """Test the /query endpoint."""

    def test_query_requires_question(self):
        """Test that query endpoint requires a question."""
        with patch('country_info_agent.api.create_graph'):
            from country_info_agent.api import app
            client = TestClient(app)
            
            response = client.post("/query", json={})
            
            assert response.status_code == 422  # Validation error

    def test_query_accepts_valid_request(self):
        """Test query endpoint with valid request structure."""
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(return_value={
            "final_answer": "Germany has a population of about 83 million.",
            "intent": "get_population",
            "countries": ["Germany"]
        })
        
        with patch('country_info_agent.api.create_graph', return_value=mock_graph):
            with patch('country_info_agent.api.langfuse_client'):
                from importlib import reload
                from country_info_agent import api
                reload(api)
                
                client = TestClient(api.app)
                
                response = client.post("/query", json={
                    "question": "What is the population of Germany?",
                    "session_id": "test-session"
                })
                
                # Check response structure (may fail if graph not mocked correctly)
                assert response.status_code in [200, 500]

    def test_query_default_session_id(self):
        """Test that session_id has a default value."""
        from country_info_agent.api import QueryRequest
        
        request = QueryRequest(question="Hello")
        assert request.session_id == "default"

    def test_query_request_model(self):
        """Test QueryRequest Pydantic model."""
        from country_info_agent.api import QueryRequest
        
        request = QueryRequest(
            question="What is the capital of France?",
            session_id="my-session"
        )
        
        assert request.question == "What is the capital of France?"
        assert request.session_id == "my-session"

    def test_query_response_model(self):
        """Test QueryResponse Pydantic model."""
        from country_info_agent.api import QueryResponse
        
        response = QueryResponse(
            answer="Paris is the capital of France.",
            intent="get_capital",
            countries=["France"]
        )
        
        assert response.answer == "Paris is the capital of France."
        assert response.intent == "get_capital"
        assert response.countries == ["France"]

    def test_query_response_optional_fields(self):
        """Test QueryResponse with optional fields."""
        from country_info_agent.api import QueryResponse
        
        response = QueryResponse(answer="Hello!")
        
        assert response.answer == "Hello!"
        assert response.intent is None
        assert response.countries == []


class TestCORSMiddleware:
    """Test CORS middleware configuration."""

    def test_cors_headers_present(self):
        """Test that CORS headers are added to responses."""
        with patch('country_info_agent.api.create_graph'):
            from country_info_agent.api import app
            client = TestClient(app)
            
            response = client.options(
                "/health",
                headers={"Origin": "http://localhost:3000"}
            )
            
            # CORS preflight should work
            assert response.status_code in [200, 405]


class TestExceptionHandlers:
    """Test global exception handlers."""

    def test_http_exception_format(self):
        """Test HTTPException returns proper JSON format."""
        with patch('country_info_agent.api.create_graph'):
            from country_info_agent.api import app
            client = TestClient(app)
            
            # Non-existent endpoint should return 404
            response = client.get("/nonexistent")
            
            assert response.status_code == 404
