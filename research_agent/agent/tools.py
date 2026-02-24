"""
Tool definitions and wrappers for the NEXUS research agent.

Provides three search tools powered by the Tavily API:
- web_search: general web search with advanced depth
- scholar_search: academic-filtered search (arXiv, PubMed, etc.)
- news_search: recent news search with configurable recency window

Also includes a URL source-type classifier for reliability scoring.
"""

import sys
import os
import structlog

# Add parent directory to path for config import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tavily import TavilyClient
from config import settings

log = structlog.get_logger()

# ── Initialize Tavily client with API key ──
tavily = TavilyClient(api_key=settings.tavily_api_key)


def classify_source_type(url: str) -> str:
    """
    Classify a URL into a source type for reliability scoring.

    Categories (highest to lowest reliability):
        academic → official → news → web (fallback)

    Args:
        url: The URL string to classify.

    Returns:
        One of: "academic", "official", "news", "web"
    """
    academic_domains = [
        "arxiv", "pubmed", "scholar", "jstor", "semantic",
        "researchgate", "springer", "nature", "science",
        "ieee", "acm.org", "doi.org"
    ]
    official_domains = [
        "gov", "who.int", "un.org", "worldbank", "imf.org",
        "oecd.org", "wef.org", "europa.eu", "cdc.gov"
    ]
    news_domains = [
        "reuters", "bbc", "nytimes", "guardian", "wsj",
        "bloomberg", "apnews", "cnbc", "economist"
    ]

    url_lower = url.lower()
    if any(d in url_lower for d in academic_domains):
        return "academic"
    if any(d in url_lower for d in official_domains):
        return "official"
    if any(d in url_lower for d in news_domains):
        return "news"
    return "web"


def web_search(query: str, max_results: int = 8) -> list[dict]:
    """
    Execute a general web search via the Tavily API.

    Uses the 'advanced' search depth for higher quality results.
    Each result is enriched with a source_type classification.

    Args:
        query: The search query string.
        max_results: Maximum number of results to return.

    Returns:
        A list of dicts with keys: url, title, content, score, source_type.
    """
    try:
        log.info("web_search.start", query=query, max_results=max_results)
        response = tavily.search(
            query=query,
            search_depth="advanced",
            max_results=max_results,
            include_answer=True,
            include_raw_content=False,
        )
        results = []
        for r in response.get("results", []):
            results.append({
                "url": r.get("url", ""),
                "title": r.get("title", ""),
                "content": r.get("content", ""),
                "score": r.get("score", 0.0),
                "source_type": classify_source_type(r.get("url", "")),
            })
        log.info("web_search.complete", results_count=len(results))
        return results
    except Exception as e:
        log.error("web_search.error", error=str(e))
        return [{"error": str(e), "url": "", "title": "", "content": "", "score": 0.0, "source_type": "web"}]


def scholar_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Search academic sources via Tavily with site-scoped filters.

    Appends academic site filters (arXiv, PubMed, JSTOR, Semantic Scholar)
    to the query for higher precision on scholarly content.

    Args:
        query: The research query string.
        max_results: Maximum number of results to return.

    Returns:
        A list of dicts with keys: url, title, content, score, source_type.
    """
    try:
        academic_query = (
            f"{query} site:scholar.google.com OR site:arxiv.org "
            f"OR site:pubmed.ncbi.nlm.nih.gov OR site:jstor.org "
            f"OR site:semanticscholar.org"
        )
        log.info("scholar_search.start", query=academic_query, max_results=max_results)
        response = tavily.search(
            query=academic_query,
            search_depth="advanced",
            max_results=max_results,
        )
        results = []
        for r in response.get("results", []):
            results.append({
                "url": r.get("url", ""),
                "title": r.get("title", ""),
                "content": r.get("content", ""),
                "score": r.get("score", 0.0),
                "source_type": "academic",
            })
        log.info("scholar_search.complete", results_count=len(results))
        return results
    except Exception as e:
        log.error("scholar_search.error", error=str(e))
        return [{"error": str(e), "url": "", "title": "", "content": "", "score": 0.0, "source_type": "academic"}]


def news_search(query: str, days_back: int = 90) -> list[dict]:
    """
    Search recent news via Tavily's news topic endpoint.

    Args:
        query: The news search query string.
        days_back: How many days back to search (default: 90).

    Returns:
        A list of dicts with keys: url, title, content, score, source_type, published_date.
    """
    try:
        log.info("news_search.start", query=query, days_back=days_back)
        response = tavily.search(
            query=query,
            topic="news",
            days=days_back,
            max_results=6,
        )
        results = []
        for r in response.get("results", []):
            results.append({
                "url": r.get("url", ""),
                "title": r.get("title", ""),
                "content": r.get("content", ""),
                "score": r.get("score", 0.0),
                "source_type": "news",
                "published_date": r.get("published_date", ""),
            })
        log.info("news_search.complete", results_count=len(results))
        return results
    except Exception as e:
        log.error("news_search.error", error=str(e))
        return [{"error": str(e), "url": "", "title": "", "content": "", "score": 0.0, "source_type": "news"}]


# ── Tool map for dynamic dispatch from nodes ──
TOOL_MAP: dict[str, callable] = {
    "web_search": web_search,
    "scholar_search": scholar_search,
    "news_search": news_search,
}
