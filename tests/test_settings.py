"""
Tests for the configuration settings module.
"""
import pytest
import os
from unittest.mock import patch


class TestSettings:
    """Test suite for Settings configuration."""

    def test_settings_loads_defaults(self):
        """Test that settings loads with default values."""
        from country_info_agent.config.settings import Settings
        
        settings = Settings()
        assert settings.openai_model == "gpt-3.5-turbo"
        assert settings.gemini_model == "gemini-2.0-flash"
        assert settings.rest_countries_base_url == "https://restcountries.com/v3.1/name"
        assert settings.cors_origins == ["*"]

    def test_settings_attributes_are_configurable(self):
        """Test that settings has configurable attributes."""
        from country_info_agent.config.settings import Settings
        
        # Verify the Settings class has the expected fields
        settings = Settings()
        
        # These should all be accessible
        assert hasattr(settings, 'openai_model')
        assert hasattr(settings, 'gemini_model')
        assert hasattr(settings, 'cors_origins')
        assert hasattr(settings, 'rest_countries_base_url')

    def test_settings_singleton_exists(self):
        """Test that settings singleton is exported."""
        from country_info_agent.config.settings import settings
        
        assert settings is not None
        assert hasattr(settings, 'openai_api_key')
        assert hasattr(settings, 'openai_model')
        assert hasattr(settings, 'gemini_model')
        assert hasattr(settings, 'rest_countries_base_url')
        assert hasattr(settings, 'cors_origins')
        assert hasattr(settings, 'langfuse_public_key')
