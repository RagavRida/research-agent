"""
Structured JSON logging service for the NEXUS research agent.

Configures Python's structlog library for JSON-formatted output with
timestamps, log levels, and caller information. Provides a helper
to log complete agent run summaries.
"""

import structlog
import logging
from typing import Any


def configure_logging(log_level: str = "INFO") -> None:
    """
    Configure structlog for JSON-based structured logging.

    Call this once at application startup (in main.py).

    Args:
        log_level: Python log level string (DEBUG, INFO, WARNING, ERROR).
    """
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def log_agent_run_summary(
    run_id: str,
    query: str,
    total_duration_ms: float,
    total_iterations: int,
    final_confidence: float,
    sources_count: int,
    tool_usage: dict[str, int],
    status: str = "success",
) -> None:
    """
    Log a structured summary of a completed agent run.

    Args:
        run_id: Unique identifier for this run.
        query: The original research query.
        total_duration_ms: Total wall-clock time in milliseconds.
        total_iterations: Number of search-evaluate iterations.
        final_confidence: Final confidence score (0-100).
        sources_count: Total number of sources collected.
        tool_usage: Tool call counts by name.
        status: Run status (success / error).
    """
    log = structlog.get_logger()
    log.info(
        "agent_run.summary",
        run_id=run_id,
        query=query,
        status=status,
        total_duration_ms=round(total_duration_ms, 2),
        total_iterations=total_iterations,
        final_confidence=final_confidence,
        sources_count=sources_count,
        tool_usage=tool_usage,
    )


def log_step(
    run_id: str,
    step_id: int,
    step_type: str,
    duration_ms: float,
    extra: dict[str, Any] | None = None,
) -> None:
    """
    Log a single agent thinking step.

    Args:
        run_id: Unique identifier for this run.
        step_id: Sequential step number.
        step_type: Type of step (plan, search, evaluate, synthesize).
        duration_ms: Step execution time in milliseconds.
        extra: Additional key-value pairs to include in the log.
    """
    log = structlog.get_logger()
    log_data: dict[str, Any] = {
        "run_id": run_id,
        "step_id": step_id,
        "step_type": step_type,
        "duration_ms": round(duration_ms, 2),
    }
    if extra:
        log_data.update(extra)

    log.info("agent_run.step", **log_data)
