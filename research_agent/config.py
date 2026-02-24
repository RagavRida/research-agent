"""
Application configuration via pydantic-settings.
Loads environment variables from .env file.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Central configuration for the NEXUS Research Agent."""

    # ── LLM Provider Toggle ──
    llm_provider: str = Field(default="gemini", env="LLM_PROVIDER")  # "gemini" or "groq"

    # ── Gemini Configuration ──
    google_api_key: str = Field(default="", env="GOOGLE_API_KEY")
    gemini_model_fast: str = "gemini-2.0-flash"
    gemini_model_pro: str = "gemini-1.5-pro"

    # ── Groq Configuration ──
    groq_api_key: str = Field(default="", env="GROQ_API_KEY")
    groq_model_fast: str = "llama-3.1-8b-instant"
    groq_model_pro: str = "llama-3.3-70b-versatile"

    # ── Tool Configuration ──
    tavily_api_key: str = Field(..., env="TAVILY_API_KEY")

    # ── Agent Behavior ──
    max_iterations: int = 8
    confidence_threshold: float = 85.0
    min_sources_required: int = 3

    # ── Streaming ──
    stream_delay_ms: int = 50

    # ── CORS ──
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
