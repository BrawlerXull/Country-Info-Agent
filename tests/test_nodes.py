"""
Tests for LangGraph node functions.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import BaseModel


class TestInvokeTool:
    """Test suite for invoke_tool node."""

    @pytest.mark.asyncio
    async def test_invoke_tool_with_countries(self, mock_agent_state, mock_runnable_config, mock_country_data):
        """Test invoke_tool fetches data for countries."""
        from country_info_agent.utils.nodes import invoke_tool
        
        state = {
            **mock_agent_state,
            "intent": "get_population",
            "countries": ["Germany"]
        }
        
        with patch('country_info_agent.utils.nodes.fetch_country_info') as mock_fetch:
            mock_fetch.return_value = {"status": "success", "data": mock_country_data}
            
            result = await invoke_tool(state, mock_runnable_config)
            
            assert "tool_outputs" in result
            assert "Germany" in result["tool_outputs"]
            assert result["tool_outputs"]["Germany"]["status"] == "success"

    @pytest.mark.asyncio
    async def test_invoke_tool_unknown_intent(self, mock_agent_state, mock_runnable_config):
        """Test invoke_tool returns empty for unknown intent."""
        from country_info_agent.utils.nodes import invoke_tool
        
        state = {
            **mock_agent_state,
            "intent": "unknown",
            "countries": []
        }
        
        result = await invoke_tool(state, mock_runnable_config)
        
        assert result["tool_outputs"] == {}

    @pytest.mark.asyncio
    async def test_invoke_tool_no_countries(self, mock_agent_state, mock_runnable_config):
        """Test invoke_tool handles empty countries list."""
        from country_info_agent.utils.nodes import invoke_tool
        
        state = {
            **mock_agent_state,
            "intent": "get_capital",
            "countries": []
        }
        
        result = await invoke_tool(state, mock_runnable_config)
        
        assert result["tool_outputs"] == {}

    @pytest.mark.asyncio 
    async def test_invoke_tool_multiple_countries(self, mock_agent_state, mock_runnable_config, mock_country_data, mock_india_data):
        """Test invoke_tool with multiple countries."""
        from country_info_agent.utils.nodes import invoke_tool
        
        state = {
            **mock_agent_state,
            "intent": "comparison",
            "countries": ["Germany", "India"]
        }
        
        async def mock_fetch(country):
            if country == "Germany":
                return {"status": "success", "data": mock_country_data}
            elif country == "India":
                return {"status": "success", "data": mock_india_data}
        
        with patch('country_info_agent.utils.nodes.fetch_country_info', side_effect=mock_fetch):
            result = await invoke_tool(state, mock_runnable_config)
            
            assert len(result["tool_outputs"]) == 2
            assert "Germany" in result["tool_outputs"]
            assert "India" in result["tool_outputs"]


class TestIdentifyIntent:
    """Test suite for identify_intent node."""

    @pytest.mark.asyncio
    async def test_identify_intent_returns_schema(self, mock_agent_state, mock_runnable_config):
        """Test that identify_intent returns proper schema."""
        from country_info_agent.utils.nodes import identify_intent, IntentSchema
        
        # Create a proper mock result
        mock_result = IntentSchema(
            intent="get_population",
            countries=["Germany"]
        )
        
        # Mock the entire chain execution
        with patch('country_info_agent.utils.nodes.get_llm') as mock_get_llm:
            mock_llm = MagicMock()
            mock_structured = MagicMock()
            # The chain (prompt | structured_llm) returns a runnable that has ainvoke
            mock_structured.ainvoke = AsyncMock(return_value=mock_result)
            mock_llm.with_structured_output.return_value = mock_structured
            mock_get_llm.return_value = mock_llm
            
            # We need to also mock the prompt | structured_llm chain
            with patch('country_info_agent.utils.nodes.ChatPromptTemplate') as mock_prompt_cls:
                mock_prompt = MagicMock()
                mock_chain = MagicMock()
                mock_chain.ainvoke = AsyncMock(return_value=mock_result)
                mock_prompt.__or__ = MagicMock(return_value=mock_chain)
                mock_prompt_cls.from_messages.return_value = mock_prompt
                
                result = await identify_intent(mock_agent_state, mock_runnable_config)
                
                assert "intent" in result
                assert "countries" in result
                assert result["intent"] == "get_population"
                assert result["countries"] == ["Germany"]

    @pytest.mark.asyncio
    async def test_identify_intent_handles_error(self, mock_agent_state, mock_runnable_config):
        """Test that identify_intent handles errors gracefully."""
        from country_info_agent.utils.nodes import identify_intent
        
        # Mock the chain to raise an exception
        with patch('country_info_agent.utils.nodes.get_llm') as mock_get_llm:
            mock_llm = MagicMock()
            mock_structured = MagicMock()
            mock_llm.with_structured_output.return_value = mock_structured
            mock_get_llm.return_value = mock_llm
            
            with patch('country_info_agent.utils.nodes.ChatPromptTemplate') as mock_prompt_cls:
                mock_prompt = MagicMock()
                mock_chain = MagicMock()
                mock_chain.ainvoke = AsyncMock(side_effect=Exception("LLM Error"))
                mock_prompt.__or__ = MagicMock(return_value=mock_chain)
                mock_prompt_cls.from_messages.return_value = mock_prompt
                
                result = await identify_intent(mock_agent_state, mock_runnable_config)
                
                assert result["intent"] == "unknown"
                assert result["countries"] == []
                assert "error" in result


class TestIntentSchema:
    """Test the IntentSchema Pydantic model."""

    def test_intent_schema_valid(self):
        """Test valid IntentSchema creation."""
        from country_info_agent.utils.nodes import IntentSchema
        
        schema = IntentSchema(intent="get_population", countries=["Germany", "France"])
        
        assert schema.intent == "get_population"
        assert schema.countries == ["Germany", "France"]

    def test_intent_schema_empty_countries(self):
        """Test IntentSchema with empty countries."""
        from country_info_agent.utils.nodes import IntentSchema
        
        schema = IntentSchema(intent="unknown", countries=[])
        
        assert schema.intent == "unknown"
        assert schema.countries == []
