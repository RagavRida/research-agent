"""
Pydantic v2 request/response models for the NEXUS Research Agent API.
"""

from pydantic import BaseModel, Field
from typing import Optional


class ResearchRequest(BaseModel):
    """Request body for the /api/research endpoint."""
    query: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="The research question to investigate",
        examples=["What are the latest advances in quantum computing?"],
    )
    max_iterations: Optional[int] = Field(
        default=8,
        ge=1,
        le=15,
        description="Maximum search-evaluate-retry iterations",
    )
    confidence_threshold: Optional[float] = Field(
        default=85.0,
        ge=50.0,
        le=99.0,
        description="Minimum confidence % to stop searching",
    )


class ResearchResponse(BaseModel):
    """Full response from a completed research run."""
    run_id: str
    query: str
    status: str
    final_answer: Optional[str] = None
    confidence: Optional[float] = None
    citations: list[dict] = []
    caveats: list[str] = []
    thinking_log: list[dict] = []
    tool_usage: dict[str, int] = {}
    total_duration_ms: float
    total_iterations: int
    contradictions_found: list[str] = []


class StreamEvent(BaseModel):
    """A single SSE event emitted during streaming research."""
    event_type: str  # "step" | "complete" | "error"
    data: dict


class HealthResponse(BaseModel):
    """Response for the /api/health endpoint."""
    status: str
    model_fast: str
    model_pro: str
    tavily_connected: bool
    timestamp: str


class AgentConfigResponse(BaseModel):
    """Response for the /api/agent/config endpoint."""
    max_iterations: int
    confidence_threshold: float
    min_sources_required: int
    gemini_model_fast: str
    gemini_model_pro: str
    stream_delay_ms: int


class ModelSwitchRequest(BaseModel):
    """Request body for switching LLM provider at runtime."""
    provider: str = Field(
        ...,
        description="LLM provider: 'gemini' or 'groq'",
        examples=["groq"],
    )
    model: Optional[str] = Field(
        default=None,
        description="Specific model name (uses provider default if omitted)",
        examples=["llama-3.3-70b-versatile"],
    )


class AvailableModelsResponse(BaseModel):
    """Response listing available models."""
    active_provider: str
    active_model: str
    providers: list[dict]

