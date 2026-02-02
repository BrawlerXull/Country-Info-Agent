"""
Tests for the REST Countries API tool.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx


class TestFetchCountryInfo:
    """Test suite for fetch_country_info function."""

    @pytest.mark.asyncio
    async def test_fetch_country_exact_match(self, mock_country_data):
        """Test fetching country with exact match."""
        from country_info_agent.utils.tools import fetch_country_info
        
        # Clear the cache for clean test
        fetch_country_info.cache_clear()
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [mock_country_data]
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance
            
            result = await fetch_country_info("Germany")
            
            assert result["status"] == "success"
            assert result["data"]["name"]["common"] == "Germany"
            assert result["data"]["population"] == 83240525

    @pytest.mark.asyncio
    async def test_fetch_country_not_found(self):
        """Test fetching a country that doesn't exist."""
        from country_info_agent.utils.tools import fetch_country_info
        
        fetch_country_info.cache_clear()
        
        mock_response = MagicMock()
        mock_response.status_code = 404
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance
            
            result = await fetch_country_info("Narnia")
            
            assert result["status"] == "error"
            assert "not found" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_fetch_country_network_error(self):
        """Test handling network errors."""
        from country_info_agent.utils.tools import fetch_country_info
        
        fetch_country_info.cache_clear()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.side_effect = httpx.RequestError("Connection failed")
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance
            
            result = await fetch_country_info("Germany")
            
            assert result["status"] == "error"
            assert "network error" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_fetch_country_caching(self, mock_country_data):
        """Test that results are cached."""
        from country_info_agent.utils.tools import fetch_country_info
        
        fetch_country_info.cache_clear()
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [mock_country_data]
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance
            
            # Call twice
            result1 = await fetch_country_info("Germany")
            result2 = await fetch_country_info("Germany")
            
            # Should only call API once due to caching
            assert mock_instance.get.call_count == 1
            assert result1 == result2
