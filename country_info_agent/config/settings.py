"""
Centralized configuration using Pydantic Settings.
All hardcoded values are now configurable via environment variables.
"""
import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # OpenAI Configuration
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = "gpt-3.5-turbo"
    
    # Google Gemini Configuration (fallback)
    google_api_key: Optional[str] = os.getenv("GOOGLE_API_KEY")
    gemini_model: str = "gemini-2.0-flash"
    
    # REST Countries API
    rest_countries_base_url: str = "https://restcountries.com/v3.1/name"
    
    # CORS Configuration
    cors_origins: List[str] = ["*"]  # Override in production!
    
    # Langfuse Configuration
    langfuse_public_key: Optional[str] = os.getenv("LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: Optional[str] = os.getenv("LANGFUSE_SECRET_KEY")
    langfuse_host: str = "https://cloud.langfuse.com"
    
    class Config:
        env_file = ".env"
        extra = "ignore"


# Singleton settings instance
settings = Settings()
