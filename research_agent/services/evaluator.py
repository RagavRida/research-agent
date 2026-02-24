"""
Confidence scoring service for the NEXUS research agent.

Provides utilities for computing aggregate confidence scores based on
source reliability, coverage breadth, and recency. Used by the evaluator
node as a supplementary scoring mechanism.
"""

from typing import Any
import structlog

log = structlog.get_logger()

# Reliability weights by source type (highest = most trustworthy)
SOURCE_RELIABILITY_WEIGHTS: dict[str, float] = {
    "academic": 1.0,
    "official": 0.9,
    "news": 0.7,
    "web": 0.4,
    "blog": 0.3,
}


def compute_source_reliability(sources: list[dict[str, Any]]) -> float:
    """
    Compute the average reliability score for a list of search results.

    Each source is scored based on its source_type using predefined weights.

    Args:
        sources: List of search result dicts with a 'source_type' key.

    Returns:
        Average reliability score between 0.0 and 1.0.
    """
    if not sources:
        return 0.0

    total = 0.0
    for source in sources:
        source_type = source.get("source_type", "web")
        total += SOURCE_RELIABILITY_WEIGHTS.get(source_type, 0.3)

    avg = total / len(sources)
    log.debug("evaluator.source_reliability", count=len(sources), avg_reliability=round(avg, 3))
    return round(avg, 3)


def compute_coverage_score(
    sources: list[dict[str, Any]],
    min_sources: int = 3,
    target_sources: int = 8,
) -> float:
    """
    Compute a coverage score based on number of sources found.

    Returns a score between 0.0 and 1.0, where 1.0 means the target
    number of sources (or more) has been reached.

    Args:
        sources: List of search result dicts.
        min_sources: Minimum sources for a non-zero score.
        target_sources: Target for a perfect score.

    Returns:
        Coverage score between 0.0 and 1.0.
    """
    count = len(sources)
    if count < min_sources:
        return round(count / min_sources * 0.5, 3)  # partial credit
    if count >= target_sources:
        return 1.0
    return round(0.5 + 0.5 * (count - min_sources) / (target_sources - min_sources), 3)


def compute_diversity_score(sources: list[dict[str, Any]]) -> float:
    """
    Compute a diversity score based on the variety of source types.

    A higher score means sources come from multiple categories
    (academic, official, news, web), reducing bias risk.

    Args:
        sources: List of search result dicts with a 'source_type' key.

    Returns:
        Diversity score between 0.0 and 1.0.
    """
    if not sources:
        return 0.0

    unique_types = set(s.get("source_type", "web") for s in sources)
    max_types = len(SOURCE_RELIABILITY_WEIGHTS)
    return round(len(unique_types) / max_types, 3)


def compute_aggregate_confidence(
    sources: list[dict[str, Any]],
    llm_confidence: float,
    min_sources: int = 3,
    target_sources: int = 8,
) -> float:
    """
    Compute a weighted aggregate confidence score combining LLM assessment,
    source reliability, coverage, and diversity.

    Weights:
      - LLM self-assessed confidence: 50%
      - Source reliability:            20%
      - Coverage breadth:              20%
      - Source diversity:              10%

    Args:
        sources: All collected search results.
        llm_confidence: The LLM's self-assessed confidence (0-100).
        min_sources: Minimum sources for coverage scoring.
        target_sources: Target sources for perfect coverage.

    Returns:
        Aggregate confidence score between 0.0 and 100.0.
    """
    reliability = compute_source_reliability(sources)
    coverage = compute_coverage_score(sources, min_sources, target_sources)
    diversity = compute_diversity_score(sources)

    aggregate = (
        llm_confidence * 0.5
        + reliability * 100 * 0.2
        + coverage * 100 * 0.2
        + diversity * 100 * 0.1
    )

    result = round(min(max(aggregate, 0.0), 100.0), 2)

    log.info(
        "evaluator.aggregate_confidence",
        llm_confidence=llm_confidence,
        reliability=reliability,
        coverage=coverage,
        diversity=diversity,
        aggregate=result,
    )

    return result
