"""
Multi-source synthesis service for the NEXUS research agent.

Provides helper utilities for deduplicating sources, resolving
contradictions, and formatting citations for the final answer.
"""

from typing import Any
import structlog

log = structlog.get_logger()


def deduplicate_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Remove duplicate search results based on URL.

    Keeps the first occurrence (highest scored) of each unique URL.

    Args:
        sources: List of search result dicts.

    Returns:
        Deduplicated list of search results.
    """
    seen_urls: set[str] = set()
    unique: list[dict[str, Any]] = []

    for source in sources:
        url = source.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique.append(source)
        elif not url:
            unique.append(source)  # keep sources without URLs

    removed = len(sources) - len(unique)
    if removed > 0:
        log.info("synthesizer.deduplicate", original=len(sources), unique=len(unique), removed=removed)

    return unique


def rank_sources_by_reliability(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Sort sources by reliability tier, then by search relevance score.

    Reliability order: academic > official > news > web > blog

    Args:
        sources: List of search result dicts.

    Returns:
        Sorted list with most reliable sources first.
    """
    reliability_order = {
        "academic": 0,
        "official": 1,
        "news": 2,
        "web": 3,
        "blog": 4,
    }

    return sorted(
        sources,
        key=lambda s: (
            reliability_order.get(s.get("source_type", "web"), 5),
            -s.get("score", 0.0),
        ),
    )


def format_citation(source: dict[str, Any], citation_id: int) -> dict[str, Any]:
    """
    Format a source into a citation object for the final answer.

    Args:
        source: A single search result dict.
        citation_id: Sequential citation number.

    Returns:
        Citation dict with id, url, title, source_type, and reliability.
    """
    source_type = source.get("source_type", "web")
    reliability_map = {
        "academic": "HIGH",
        "official": "HIGH",
        "news": "MEDIUM",
        "web": "LOW",
        "blog": "LOW",
    }

    return {
        "id": f"SOURCE_{citation_id}",
        "url": source.get("url", ""),
        "title": source.get("title", "Untitled"),
        "source_type": source_type,
        "reliability": reliability_map.get(source_type, "LOW"),
    }


def prepare_sources_for_synthesis(
    all_results: list[dict[str, Any]],
    max_sources: int = 15,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Prepare search results for synthesis: deduplicate, rank, limit, and
    generate citation objects.

    Args:
        all_results: All accumulated search results from the agent.
        max_sources: Maximum number of sources to include.

    Returns:
        Tuple of (ranked_sources, citations).
    """
    unique = deduplicate_sources(all_results)
    ranked = rank_sources_by_reliability(unique)
    top_sources = ranked[:max_sources]

    citations = [
        format_citation(source, i + 1)
        for i, source in enumerate(top_sources)
    ]

    log.info(
        "synthesizer.prepare",
        total_input=len(all_results),
        deduplicated=len(unique),
        selected=len(top_sources),
        citations=len(citations),
    )

    return top_sources, citations


def extract_key_claims(sources: list[dict[str, Any]]) -> list[str]:
    """
    Extract key content snippets from top sources for contradiction detection.

    Returns the first 200 characters of each source's content.

    Args:
        sources: Ranked list of search results.

    Returns:
        List of content snippet strings.
    """
    claims: list[str] = []
    for source in sources[:10]:
        content = source.get("content", "").strip()
        if content:
            claims.append(content[:200])
    return claims
