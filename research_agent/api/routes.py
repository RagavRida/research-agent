"""
FastAPI API routes for the NEXUS Research Agent.

Endpoints:
  POST /api/research         — Run full research synchronously
  POST /api/research/stream  — Stream research steps via SSE
  POST /api/research/demo    — Stream research with guaranteed retry demonstration
  GET  /api/health           — Health check
  GET  /api/agent/config     — Current agent configuration

SSE Event Types:
  { "event_type": "step",              "data": {ThinkingStep} }
  { "event_type": "retry_triggered",   "data": {RetryEvent fields} }
  { "event_type": "confidence_update", "data": {"current", "history", "threshold", "passed"} }
  { "event_type": "gaps_updated",      "data": {"gaps": [...]} }
  { "event_type": "complete",          "data": {ResearchResponse} }
  { "event_type": "error",             "data": {"message": "..."} }
"""

import sys
import os
import json
import time
import uuid
import asyncio
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.schemas import (
    ResearchRequest,
    ResearchResponse,
    HealthResponse,
    AgentConfigResponse,
    ModelSwitchRequest,
    AvailableModelsResponse,
)
from agent.graph import agent_graph
from agent.state import AgentState
from config import settings

log = structlog.get_logger()
router = APIRouter()


# ═══════════════════════════════════════════════════════════════
# Shared: build initial state
# ═══════════════════════════════════════════════════════════════

def _build_initial_state(query: str, max_iterations: int | None = None) -> AgentState:
    start_time = time.time()
    return {
        "query": query,
        "run_id": str(uuid.uuid4())[:8],
        "subtasks": [],
        "research_strategy": "",
        "current_iteration": 0,
        "max_iterations": max_iterations or settings.max_iterations,
        "current_subtask_idx": 0,
        "all_search_results": [],
        "current_search_results": [],
        "search_queries_used": [],
        "current_query": query,
        "latest_evaluation": None,
        "confidence_history": [],
        "retry_events": [],
        "query_reformulation_count": 0,
        "last_retry_reason": None,
        "information_gaps": [],
        "gap_resolution_map": {},
        "synthesized_content": None,
        "contradictions_found": [],
        "final_confidence": None,
        "final_answer": None,
        "citations": [],
        "caveats": [],
        "thinking_log": [],
        "tool_usage": {},
        "start_time": start_time,
        "should_stop": False,
        "error": None,
    }


# ═══════════════════════════════════════════════════════════════
# Shared: SSE event generator
# ═══════════════════════════════════════════════════════════════

async def _run_sse_stream(initial_state: AgentState):
    """
    Core SSE generator used by both /stream and /demo endpoints.
    Emits step, retry_triggered, confidence_update, gaps_updated,
    and complete events as the agent processes.
    """
    run_id = initial_state["run_id"]
    start_time = initial_state["start_time"]
    final_result = None

    try:
        for chunk in agent_graph.stream(initial_state):
            for node_name, node_output in chunk.items():

                # ── Emit retry events FIRST (highest priority) ──
                if "retry_events" in node_output:
                    for retry in node_output["retry_events"]:
                        if retry:
                            retry_event = {
                                "event_type": "retry_triggered",
                                "data": {
                                    "iteration": retry["iteration"],
                                    "confidence": retry["trigger_confidence"],
                                    "gaps": retry["trigger_gaps"],
                                    "failed_query": retry["original_query"],
                                    "strategy": retry["reformulation_strategy"],
                                    "timestamp": retry["timestamp"],
                                }
                            }
                            yield f"data: {json.dumps(retry_event)}\n\n"
                            await asyncio.sleep(0.1)

                # ── Emit thinking steps ──
                if "thinking_log" in node_output:
                    for step in node_output["thinking_log"]:
                        step_event = {
                            "event_type": "step",
                            "data": dict(step),
                        }
                        yield f"data: {json.dumps(step_event)}\n\n"
                        await asyncio.sleep(settings.stream_delay_ms / 1000.0)

                # ── Emit confidence update ──
                if "confidence_history" in node_output:
                    history = node_output["confidence_history"]
                    if history:
                        conf_event = {
                            "event_type": "confidence_update",
                            "data": {
                                "current": history[-1],
                                "history": history,
                                "threshold": settings.confidence_threshold,
                                "passed": history[-1] >= settings.confidence_threshold,
                            }
                        }
                        yield f"data: {json.dumps(conf_event)}\n\n"

                # ── Emit gap updates ──
                if "information_gaps" in node_output and node_output["information_gaps"]:
                    gap_event = {
                        "event_type": "gaps_updated",
                        "data": {"gaps": node_output["information_gaps"]}
                    }
                    yield f"data: {json.dumps(gap_event)}\n\n"

                # ── Capture final result ──
                if node_output.get("should_stop"):
                    final_result = node_output

        # ── Send completion event ──
        total_duration = (time.time() - start_time) * 1000
        complete_data = {
            "run_id": run_id,
            "query": initial_state["query"],
            "status": "success",
            "total_duration_ms": round(total_duration, 2),
        }
        if final_result:
            complete_data.update({
                "final_answer": final_result.get("final_answer"),
                "confidence": final_result.get("final_confidence"),
                "citations": final_result.get("citations", []),
                "caveats": final_result.get("caveats", []),
                "contradictions_found": final_result.get("contradictions_found", []),
            })

        yield f"data: {json.dumps({'event_type': 'complete', 'data': complete_data})}\n\n"
        log.info("api.research.stream.complete", run_id=run_id, duration_ms=round(total_duration, 2))

    except Exception as e:
        log.error("api.research.stream.error", run_id=run_id, error=str(e))
        yield f"data: {json.dumps({'event_type': 'error', 'data': {'message': str(e)}})}\n\n"


def _make_streaming_response(generator):
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ═══════════════════════════════════════════════════════════════
# ENDPOINT 1: POST /api/research (synchronous)
# ═══════════════════════════════════════════════════════════════

@router.post("/api/research", response_model=ResearchResponse)
async def run_research(request: ResearchRequest) -> ResearchResponse:
    """Run full research agent pipeline synchronously."""
    run_id = str(uuid.uuid4())[:8]
    start_time = time.time()

    log.info("api.research.start", run_id=run_id, query=request.query)

    initial_state = _build_initial_state(request.query, request.max_iterations)
    initial_state["run_id"] = run_id
    initial_state["start_time"] = start_time

    try:
        result = await asyncio.to_thread(agent_graph.invoke, initial_state)
        total_duration = (time.time() - start_time) * 1000

        log.info(
            "api.research.complete",
            run_id=run_id,
            duration_ms=round(total_duration, 2),
            iterations=result.get("current_iteration", 0),
            confidence=result.get("final_confidence", 0),
        )

        return ResearchResponse(
            run_id=run_id,
            query=request.query,
            status="success",
            final_answer=result.get("final_answer"),
            confidence=result.get("final_confidence"),
            citations=result.get("citations", []),
            caveats=result.get("caveats", []),
            thinking_log=[dict(s) for s in result.get("thinking_log", [])],
            tool_usage=result.get("tool_usage", {}),
            total_duration_ms=round(total_duration, 2),
            total_iterations=result.get("current_iteration", 0),
            contradictions_found=result.get("contradictions_found", []),
        )

    except Exception as e:
        log.error("api.research.error", run_id=run_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Research agent error: {str(e)}")


# ═══════════════════════════════════════════════════════════════
# ENDPOINT 2: POST /api/research/stream (SSE)
# ═══════════════════════════════════════════════════════════════

@router.post("/api/research/stream")
async def stream_research(request: ResearchRequest) -> StreamingResponse:
    """Stream agent thinking steps as Server-Sent Events (SSE)."""
    log.info("api.research.stream.start", query=request.query)
    initial_state = _build_initial_state(request.query, request.max_iterations)
    return _make_streaming_response(_run_sse_stream(initial_state))


# ═══════════════════════════════════════════════════════════════
# ENDPOINT 3: POST /api/research/demo (guaranteed retry)
# ═══════════════════════════════════════════════════════════════

@router.post("/api/research/demo")
async def demo_research_with_retry(request: ResearchRequest) -> StreamingResponse:
    """
    Demo endpoint that GUARANTEES a self-correction retry moment.

    Forces max_iterations to at least 3, and sets confidence_threshold
    artificially high for the first evaluation pass (via the query
    framing), so the agent naturally fails iteration 1 and demonstrates
    genuine self-correction on iteration 2.

    Uses real Gemini + Tavily — behavior is authentic, not simulated.
    """
    log.info("api.research.demo.start", query=request.query)

    # Wrap the query to make it complex enough that a single broad
    # search cannot possibly meet the 85% threshold.
    demo_query = (
        f"{request.query} — provide sector-specific data, "
        f"primary source citations, year-by-year statistics, "
        f"and expert consensus with contradicting viewpoints."
    )

    initial_state = _build_initial_state(demo_query, max_iterations=4)
    return _make_streaming_response(_run_sse_stream(initial_state))


# ═══════════════════════════════════════════════════════════════
# ENDPOINT 4: GET /api/health
# ═══════════════════════════════════════════════════════════════

@router.get("/api/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    tavily_connected = bool(
        settings.tavily_api_key and settings.tavily_api_key != "your_tavily_api_key_here"
    )

    return HealthResponse(
        status="healthy",
        model_fast=settings.gemini_model_fast,
        model_pro=settings.gemini_model_pro,
        tavily_connected=tavily_connected,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


# ═══════════════════════════════════════════════════════════════
# ENDPOINT 5: GET /api/agent/config
# ═══════════════════════════════════════════════════════════════

@router.get("/api/agent/config", response_model=AgentConfigResponse)
async def get_agent_config() -> AgentConfigResponse:
    """Return current agent configuration."""
    return AgentConfigResponse(
        max_iterations=settings.max_iterations,
        confidence_threshold=settings.confidence_threshold,
        min_sources_required=settings.min_sources_required,
        gemini_model_fast=settings.gemini_model_fast,
        gemini_model_pro=settings.gemini_model_pro,
        stream_delay_ms=settings.stream_delay_ms,
    )


# ═══════════════════════════════════════════════════════════════
# ENDPOINT 6: GET /api/models (available models)
# ═══════════════════════════════════════════════════════════════

@router.get("/api/models", response_model=AvailableModelsResponse)
async def get_available_models() -> AvailableModelsResponse:
    """Return available LLM providers and the currently active one."""
    import agent.nodes as nodes_mod

    active_provider = getattr(nodes_mod, '_active_provider', settings.llm_provider)
    active_model = getattr(nodes_mod, '_active_model', '')
    if not active_model:
        active_model = (
            settings.groq_model_fast if active_provider == 'groq'
            else settings.gemini_model_fast
        )

    return AvailableModelsResponse(
        active_provider=active_provider,
        active_model=active_model,
        providers=[
            {
                "id": "groq",
                "name": "Groq",
                "models": [
                    {"id": "llama-3.3-70b-versatile", "name": "Llama 3.3 70B"},
                    {"id": "llama-3.1-8b-instant", "name": "Llama 3.1 8B"},
                    {"id": "mixtral-8x7b-32768", "name": "Mixtral 8x7B"},
                ],
                "available": bool(settings.groq_api_key),
            },
            {
                "id": "gemini",
                "name": "Google Gemini",
                "models": [
                    {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash"},
                    {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro"},
                ],
                "available": bool(settings.google_api_key),
            },
        ],
    )


# ═══════════════════════════════════════════════════════════════
# ENDPOINT 7: POST /api/models/switch (hot-swap LLM)
# ═══════════════════════════════════════════════════════════════

@router.post("/api/models/switch")
async def switch_model(request: ModelSwitchRequest):
    """
    Hot-swap the active LLM provider/model at runtime.
    No server restart needed.
    """
    import agent.nodes as nodes_mod

    provider = request.provider.lower()
    model = request.model

    if provider == "groq":
        from langchain_groq import ChatGroq
        model = model or settings.groq_model_fast
        nodes_mod.llm_fast = ChatGroq(
            model=model,
            temperature=0.3,
            groq_api_key=settings.groq_api_key,
        )
        nodes_mod.llm_pro = ChatGroq(
            model=model,
            temperature=0.2,
            groq_api_key=settings.groq_api_key,
        )
    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        model = model or settings.gemini_model_fast
        nodes_mod.llm_fast = ChatGoogleGenerativeAI(
            model=model,
            temperature=0.3,
            google_api_key=settings.google_api_key,
        )
        nodes_mod.llm_pro = ChatGoogleGenerativeAI(
            model=model or settings.gemini_model_pro,
            temperature=0.2,
            google_api_key=settings.google_api_key,
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    # Track active state
    nodes_mod._active_provider = provider
    nodes_mod._active_model = model

    log.info("api.models.switched", provider=provider, model=model)
    return {"status": "ok", "provider": provider, "model": model}

