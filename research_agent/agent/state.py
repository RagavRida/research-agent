"""
AgentState — the complete LangGraph state TypedDict for the NEXUS research agent.

Defines all typed structures used throughout the agent's execution lifecycle:
SubTask, SearchResult, EvaluationResult, ThinkingStep, RetryEvent, and AgentState.
"""

from typing import TypedDict, Annotated, Optional
import operator


class SubTask(TypedDict):
    """Represents a single decomposed research subtask."""
    id: str              # "T-01", "T-02"...
    task: str
    priority: str        # "HIGH" | "MED" | "LOW"
    status: str          # "pending" | "active" | "complete" | "retrying"
    tool: str            # "web_search" | "scholar_search" | "news_search"
    duration_ms: Optional[float]


class SearchResult(TypedDict):
    """A single search result from any tool."""
    url: str
    title: str
    content: str
    score: float
    source_type: str     # "news" | "academic" | "official" | "blog" | "web"


class EvaluationResult(TypedDict):
    """Output of the evaluator node — confidence score and coverage analysis."""
    confidence: float
    sources_found: int
    avg_reliability: float
    threshold_met: bool
    gaps: list[str]
    decision: str        # "sufficient" | "retry" | "force_synthesize"
    reformulation_hint: str   # how next query should differ if retrying


class ThinkingStep(TypedDict):
    """A single step in the agent's reasoning trace, streamed to the frontend."""
    step_id: int
    type: str            # "plan" | "search_initial" | "search_retry" | "evaluate_retry" | "evaluate_pass" | "synthesize" | "final"
    timestamp: str
    duration_ms: float
    thinking: str
    action: str
    data: dict
    tokens_used: int


class RetryEvent(TypedDict):
    """A formal record of a self-correction retry moment."""
    iteration: int
    trigger_confidence: float       # confidence that caused retry
    trigger_gaps: list[str]         # specific gaps identified
    original_query: str             # query that failed
    reformulated_query: str         # new query (filled in execute_search)
    reformulation_strategy: str     # why the query changed
    timestamp: str


class AgentState(TypedDict):
    """
    Complete LangGraph state for one research run.

    Fields use Annotated[list, operator.add] for append-only accumulation
    across node invocations (e.g., thinking_log, all_search_results).
    """

    # ── Input ──
    query: str
    run_id: str

    # ── Planning ──
    subtasks: list[SubTask]
    research_strategy: str

    # ── Execution tracking ──
    current_iteration: int
    max_iterations: int
    current_subtask_idx: int

    # ── Search state ──
    all_search_results: Annotated[list[SearchResult], operator.add]
    current_search_results: list[SearchResult]
    search_queries_used: list[str]
    current_query: str              # tracks the evolving search query

    # ── Evaluation ──
    latest_evaluation: Optional[EvaluationResult]
    confidence_history: list[float]

    # ── Retry / self-correction tracking ──
    retry_events: Annotated[list[RetryEvent], operator.add]
    query_reformulation_count: int  # how many times the query changed
    last_retry_reason: Optional[str]
    information_gaps: list[str]     # cumulative gaps across all iterations
    gap_resolution_map: dict        # maps gap → iteration it was resolved

    # ── Synthesis ──
    synthesized_content: Optional[str]
    contradictions_found: list[str]
    final_confidence: Optional[float]

    # ── Output ──
    final_answer: Optional[str]
    citations: list[dict]
    caveats: list[str]

    # ── Logging ──
    thinking_log: Annotated[list[ThinkingStep], operator.add]
    tool_usage: dict[str, int]
    start_time: float

    # ── Control flow ──
    should_stop: bool
    error: Optional[str]
