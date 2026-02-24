"""
LangGraph node functions for the NEXUS research agent.

Each node:
  - Takes AgentState as input
  - Returns a partial AgentState dict with updates
  - Appends a ThinkingStep to thinking_log
  - Handles exceptions gracefully with structured logging

Nodes:
  1. plan_research      — decomposes query into subtasks via CoT
  2. execute_search     — picks next search query and runs the tool (retry-aware)
  3. evaluate_results   — scores results, identifies gaps, decides retry vs. synthesize
  4. synthesize_results — merges all sources into final answer
  5. should_continue    — conditional edge function for the graph
"""

import sys
import os
import json
import time
from datetime import datetime, timezone
from typing import Any

import structlog

# Add parent directory to path for config import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import SystemMessage, HumanMessage

from agent.state import AgentState, ThinkingStep, SubTask, RetryEvent
from agent.prompts import (
    MASTER_SYSTEM_PROMPT,
    PLANNER_PROMPT,
    SEARCH_DECISION_PROMPT_V2,
    EVALUATOR_PROMPT_V2,
    SYNTHESIZER_PROMPT,
)
from agent.tools import TOOL_MAP
from config import settings

log = structlog.get_logger()

# ═══════════════════════════════════════════════════════════════
# LLM Initialization — supports Gemini and Groq
# ═══════════════════════════════════════════════════════════════

if settings.llm_provider == "groq":
    from langchain_groq import ChatGroq

    log.info("llm.provider.groq", model_fast=settings.groq_model_fast, model_pro=settings.groq_model_pro)
    llm_fast = ChatGroq(
        model=settings.groq_model_fast,
        temperature=0.3,
        groq_api_key=settings.groq_api_key,
    )
    llm_pro = ChatGroq(
        model=settings.groq_model_pro,
        temperature=0.2,
        groq_api_key=settings.groq_api_key,
    )
else:
    from langchain_google_genai import ChatGoogleGenerativeAI

    log.info("llm.provider.gemini", model_fast=settings.gemini_model_fast, model_pro=settings.gemini_model_pro)
    llm_fast = ChatGoogleGenerativeAI(
        model=settings.gemini_model_fast,
        temperature=0.3,
        google_api_key=settings.google_api_key,
    )
    llm_pro = ChatGoogleGenerativeAI(
        model=settings.gemini_model_pro,
        temperature=0.2,
        google_api_key=settings.google_api_key,
    )


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def parse_llm_json(response_text: str) -> dict:
    """
    Robustly parse JSON from an LLM response.

    Handles common LLM quirks:
    - Markdown code fences (```json ... ```)
    - Extra text before or after the JSON object
    - Multiple JSON blocks (takes the first one)
    """
    import re

    text = response_text.strip()

    # Strip markdown code fences
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:])
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3].rstrip()

    # Try direct parse first (fast path)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Extract the first balanced { ... } block using brace counting
    start_idx = text.find("{")
    if start_idx == -1:
        raise ValueError(f"No JSON object found in LLM response: {text[:200]}")

    depth = 0
    in_string = False
    escape_next = False
    end_idx = start_idx

    for i in range(start_idx, len(text)):
        ch = text[i]
        if escape_next:
            escape_next = False
            continue
        if ch == "\\":
            escape_next = True
            continue
        if ch == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end_idx = i
                break

    if depth != 0:
        # Brace counting failed, try regex fallback
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        raise ValueError(f"Unbalanced JSON in LLM response: {text[:200]}")

    json_str = text[start_idx:end_idx + 1]
    return json.loads(json_str)


def make_step_id(state: AgentState) -> int:
    """Generate the next sequential step ID."""
    return len(state.get("thinking_log", [])) + 1


def _get_system_message() -> SystemMessage:
    """Build the master system message with current settings."""
    return SystemMessage(content=MASTER_SYSTEM_PROMPT.format(
        confidence_threshold=settings.confidence_threshold,
        max_iterations=settings.max_iterations,
    ))


def _extract_tokens(response: Any) -> int:
    """Safely extract total token count from LLM response."""
    try:
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            return response.usage_metadata.get("total_tokens", 0)
    except Exception:
        pass
    return 0


# ═══════════════════════════════════════════════════════════════
# NODE 1: plan_research
# ═══════════════════════════════════════════════════════════════

def plan_research(state: AgentState) -> dict:
    """
    Decompose the user's research query into 3-5 searchable subtasks
    using Chain-of-Thought reasoning via the fast Gemini model.
    """
    start = time.time()
    step_id = make_step_id(state)

    try:
        log.info("node.plan_research.start", query=state["query"])

        prompt = PLANNER_PROMPT.format(query=state["query"])
        response = llm_fast.invoke([
            _get_system_message(),
            HumanMessage(content=prompt),
        ])

        parsed = parse_llm_json(response.content)
        duration = (time.time() - start) * 1000

        subtasks = [
            SubTask(
                id=t["id"],
                task=t["task"],
                priority=t["priority"],
                status="pending",
                tool=t["tool"],
                duration_ms=None,
            )
            for t in parsed["data"]["subtasks"]
        ]

        step = ThinkingStep(
            step_id=step_id,
            type="plan",
            timestamp=datetime.now(timezone.utc).isoformat(),
            duration_ms=round(duration, 2),
            thinking=parsed["thinking"],
            action=parsed["action"],
            data=parsed["data"],
            tokens_used=_extract_tokens(response),
        )

        log.info(
            "node.plan_research.complete",
            subtask_count=len(subtasks),
            duration_ms=round(duration, 2),
        )

        return {
            "subtasks": subtasks,
            "research_strategy": parsed["data"]["strategy"],
            "thinking_log": [step],
            "tool_usage": {},
            "retry_events": [],
            "information_gaps": [],
            "gap_resolution_map": {},
            "query_reformulation_count": 0,
            "current_query": state["query"],
        }

    except Exception as e:
        log.error("node.plan_research.error", error=str(e))
        duration = (time.time() - start) * 1000
        error_step = ThinkingStep(
            step_id=step_id,
            type="plan",
            timestamp=datetime.now(timezone.utc).isoformat(),
            duration_ms=round(duration, 2),
            thinking=f"Error during planning: {str(e)}",
            action="Planning failed — will attempt basic search",
            data={"error": str(e)},
            tokens_used=0,
        )
        fallback_subtask = SubTask(
            id="T-01",
            task=state["query"],
            priority="HIGH",
            status="pending",
            tool="web_search",
            duration_ms=None,
        )
        return {
            "subtasks": [fallback_subtask],
            "research_strategy": "Fallback: direct search due to planning error",
            "thinking_log": [error_step],
            "tool_usage": {},
            "retry_events": [],
            "information_gaps": [],
            "gap_resolution_map": {},
            "query_reformulation_count": 0,
            "current_query": state["query"],
            "error": str(e),
        }


# ═══════════════════════════════════════════════════════════════
# NODE 2: execute_search  (retry-aware)
# ═══════════════════════════════════════════════════════════════

def execute_search(state: AgentState) -> dict:
    """
    Decide the next search query using LLM reasoning, then execute it.

    On a retry, uses the evaluator's reformulation_hint to steer the
    new query rather than deciding blindly — this is what makes the
    self-correction REAL, not simulated.
    """
    start = time.time()
    step_id = make_step_id(state)

    is_retry = state["current_iteration"] > 0
    reformulation_hint = ""
    if is_retry and state.get("latest_evaluation"):
        reformulation_hint = state["latest_evaluation"].get("reformulation_hint", "")

    try:
        log.info(
            "node.execute_search.start",
            iteration=state["current_iteration"],
            is_retry=is_retry,
            reformulation_hint=reformulation_hint[:80] if reformulation_hint else "",
        )

        prompt = SEARCH_DECISION_PROMPT_V2.format(
            query=state["query"],
            iteration=state["current_iteration"],
            max_iterations=settings.max_iterations,
            previous_queries=json.dumps(state.get("search_queries_used", [])),
            gaps=json.dumps(state.get("information_gaps", [])),
            confidence=state["confidence_history"][-1] if state.get("confidence_history") else 0,
            reformulation_hint=reformulation_hint,
            is_retry=is_retry,
        )

        response = llm_fast.invoke([
            _get_system_message(),
            HumanMessage(content=prompt),
        ])

        parsed = parse_llm_json(response.content)
        search_data = parsed["data"]

        tool_name = search_data.get("tool", "web_search")
        query = search_data["query"]
        tool_fn = TOOL_MAP.get(tool_name, TOOL_MAP["web_search"])

        log.info("node.execute_search.running_tool", tool=tool_name, query=query)
        results = tool_fn(query)

        duration = (time.time() - start) * 1000

        # Build thinking text — richer on retry to show the reformulation rationale
        if is_retry:
            thinking_text = (
                f"Previous search failed confidence check. "
                f"Reformulation strategy: {search_data.get('reformulation_strategy', 'narrowing scope')}. "
                f"New query '{query}' targets specifically: "
                f"{search_data.get('targets_gap', 'identified gaps')}. "
                f"This is iteration {state['current_iteration'] + 1}. "
                f"Switching to {tool_name} for better coverage."
            )
            step_type = "search_retry"
        else:
            thinking_text = parsed["thinking"]
            step_type = "search_initial"

        # Update tool usage counters
        updated_tool_usage = dict(state.get("tool_usage", {}))
        updated_tool_usage[tool_name] = updated_tool_usage.get(tool_name, 0) + 1

        step = ThinkingStep(
            step_id=step_id,
            type=step_type,
            timestamp=datetime.now(timezone.utc).isoformat(),
            duration_ms=round(duration, 2),
            thinking=thinking_text,
            action=parsed["action"],
            data={
                **search_data,
                "results_count": len(results),
                "is_retry": is_retry,
                "iteration": state["current_iteration"] + 1,
                "previous_confidence": (
                    state["confidence_history"][-1]
                    if state.get("confidence_history") else None
                ),
                "reformulation_hint_used": reformulation_hint,
                "sources": [
                    {
                        "url": r.get("url", ""),
                        "title": r.get("title", ""),
                        "source_type": r.get("source_type", "web"),
                        "score": r.get("score", 0),
                    }
                    for r in results if r.get("url")
                ][:10],
            },
            tokens_used=_extract_tokens(response),
        )

        log.info(
            "node.execute_search.complete",
            tool=tool_name,
            results_count=len(results),
            duration_ms=round(duration, 2),
        )

        return {
            "current_search_results": results,
            "all_search_results": results,
            "search_queries_used": state.get("search_queries_used", []) + [query],
            "current_query": query,
            "thinking_log": [step],
            "tool_usage": updated_tool_usage,
            "current_iteration": state["current_iteration"] + 1,
            "query_reformulation_count": (
                state.get("query_reformulation_count", 0) + (1 if is_retry else 0)
            ),
        }

    except Exception as e:
        log.error("node.execute_search.error", error=str(e))
        duration = (time.time() - start) * 1000
        error_step = ThinkingStep(
            step_id=step_id,
            type="search_initial",
            timestamp=datetime.now(timezone.utc).isoformat(),
            duration_ms=round(duration, 2),
            thinking=f"Search execution error: {str(e)}",
            action="Search failed — will evaluate available results",
            data={"error": str(e)},
            tokens_used=0,
        )
        return {
            "current_search_results": [],
            "all_search_results": [],
            "thinking_log": [error_step],
            "current_iteration": state["current_iteration"] + 1,
            "error": str(e),
        }


# ═══════════════════════════════════════════════════════════════
# NODE 3: evaluate_results  (self-correction core)
# ═══════════════════════════════════════════════════════════════

def evaluate_results(state: AgentState) -> dict:
    """
    THE MOST IMPORTANT NODE.

    Scores the current search results against the research query.
    If confidence < threshold: explicitly explains WHY it is not enough,
    identifies SPECIFIC gaps, and signals retry with a reformulation hint.

    This produces the "aha — I don't know enough" moment in the Thinking Log.
    """
    start = time.time()
    step_id = make_step_id(state)

    try:
        results_text = json.dumps(state.get("current_search_results", [])[:6], indent=2)
        all_queries_so_far = json.dumps(state.get("search_queries_used", []))
        cumulative_gaps = json.dumps(state.get("information_gaps", []))
        iteration = state["current_iteration"]
        previous_confidence = (
            state["confidence_history"][-1]
            if state.get("confidence_history") else 0
        )

        log.info(
            "node.evaluate_results.start",
            iteration=iteration,
            results_count=len(state.get("current_search_results", [])),
        )

        prompt = EVALUATOR_PROMPT_V2.format(
            query=state["query"],
            results=results_text,
            iteration=iteration,
            max_iterations=settings.max_iterations,
            previous_confidence=previous_confidence,
            threshold=settings.confidence_threshold,
            all_queries=all_queries_so_far,
            cumulative_gaps=cumulative_gaps,
        )

        response = llm_fast.invoke([
            _get_system_message(),
            HumanMessage(content=prompt),
        ])

        parsed = parse_llm_json(response.content)
        eval_data = parsed["data"]
        duration = (time.time() - start) * 1000

        is_retry_moment = (
            not eval_data.get("threshold_met", False) and
            iteration < settings.max_iterations
        )

        gaps_identified = eval_data.get("gaps_identified", [])
        reformulation_hint = eval_data.get("reformulation_hint", "")
        current_query = state.get("current_query", state["query"])

        # ── Build ThinkingStep differently based on retry vs pass ──
        if is_retry_moment:
            # THE KEY MOMENT — agent admits it doesn't know enough
            step_type = "evaluate_retry"
            thinking_text = (
                f"I've analyzed {eval_data.get('sources_found', 0)} sources "
                f"from my search for '{current_query}'. "
                f"My confidence is only {eval_data['confidence']}% — "
                f"below the {settings.confidence_threshold}% threshold. "
                f"I'm missing critical information: "
                f"{', '.join(gaps_identified[:2]) if gaps_identified else 'insufficient coverage'}. "
                f"I cannot give a reliable answer yet. I need to search again with "
                f"a different strategy: {reformulation_hint}."
            )
            action_text = (
                f"Confidence {eval_data['confidence']}% insufficient. "
                f"Triggering self-correction — reformulating search strategy."
            )

            # Log this as a formal RetryEvent
            retry_event = RetryEvent(
                iteration=iteration,
                trigger_confidence=eval_data["confidence"],
                trigger_gaps=gaps_identified,
                original_query=current_query,
                reformulated_query="",   # filled in next execute_search call
                reformulation_strategy=reformulation_hint,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

            log.warning(
                "node.evaluate_results.retry_triggered",
                iteration=iteration,
                confidence=eval_data["confidence"],
                threshold=settings.confidence_threshold,
                gaps=gaps_identified,
                reformulation_hint=reformulation_hint[:100],
            )

        else:
            step_type = "evaluate_pass"
            thinking_text = (
                f"Search results are sufficient. Found {eval_data.get('sources_found', 0)} "
                f"relevant sources. Confidence {eval_data['confidence']}% exceeds "
                f"the {settings.confidence_threshold}% threshold. Proceeding to synthesis."
            )
            action_text = (
                f"Confidence threshold met at {eval_data['confidence']}%. Synthesizing."
            )
            retry_event = None

            log.info(
                "node.evaluate_results.threshold_met",
                confidence=eval_data["confidence"],
                iteration=iteration,
            )

        step = ThinkingStep(
            step_id=step_id,
            type=step_type,
            timestamp=datetime.now(timezone.utc).isoformat(),
            duration_ms=round(duration, 2),
            thinking=thinking_text,
            action=action_text,
            data={
                **eval_data,
                "is_retry_moment": is_retry_moment,
                "query_evaluated": current_query,
                "iteration": iteration,
                "previous_confidence": previous_confidence,
                "confidence_delta": eval_data["confidence"] - previous_confidence,
                "threshold": settings.confidence_threshold,
            },
            tokens_used=_extract_tokens(response),
        )

        # Accumulate gaps — merge new ones with existing
        new_gaps = list(set(
            state.get("information_gaps", []) + gaps_identified
        ))

        evaluation = {
            "confidence": eval_data["confidence"],
            "sources_found": eval_data.get("sources_found", 0),
            "avg_reliability": eval_data.get("avg_reliability", 0.0),
            "threshold_met": eval_data.get("threshold_met", False),
            "gaps": gaps_identified,
            "decision": eval_data.get("decision", "retry"),
            "reformulation_hint": reformulation_hint,
        }

        result = {
            "latest_evaluation": evaluation,
            "confidence_history": state.get("confidence_history", []) + [eval_data["confidence"]],
            "information_gaps": new_gaps,
            "last_retry_reason": reformulation_hint if is_retry_moment else None,
            "thinking_log": [step],
            "retry_events": [retry_event] if retry_event else [],
        }

        return result

    except Exception as e:
        log.error("node.evaluate_results.error", error=str(e))
        duration = (time.time() - start) * 1000
        error_step = ThinkingStep(
            step_id=step_id,
            type="evaluate_retry",
            timestamp=datetime.now(timezone.utc).isoformat(),
            duration_ms=round(duration, 2),
            thinking=f"Evaluation error: {str(e)}",
            action="Evaluation failed — defaulting to force_synthesize",
            data={"error": str(e)},
            tokens_used=0,
        )
        fallback_eval = {
            "confidence": 0,
            "sources_found": len(state.get("all_search_results", [])),
            "avg_reliability": 0.0,
            "threshold_met": False,
            "gaps": ["Evaluation failed"],
            "decision": "force_synthesize",
            "reformulation_hint": "",
        }
        return {
            "latest_evaluation": fallback_eval,
            "confidence_history": state.get("confidence_history", []) + [0],
            "thinking_log": [error_step],
            "retry_events": [],
        }


# ═══════════════════════════════════════════════════════════════
# NODE 4: synthesize_results
# ═══════════════════════════════════════════════════════════════

def synthesize_results(state: AgentState) -> dict:
    """
    Merge all collected search results into a comprehensive final answer.
    Resolves contradictions, generates citations, and assigns a final
    confidence score. Uses the Pro model for better long-context handling.
    """
    start = time.time()
    step_id = make_step_id(state)

    try:
        all_results = state.get("all_search_results", [])
        all_results_text = json.dumps(all_results[:15], indent=2)

        log.info(
            "node.synthesize_results.start",
            total_results=len(all_results),
            iterations=state["current_iteration"],
        )

        prompt = SYNTHESIZER_PROMPT.format(
            query=state["query"],
            all_results=all_results_text,
            confidence_history=json.dumps(state.get("confidence_history", [])),
            iterations=state["current_iteration"],
            n=len(all_results),
        )

        response = llm_pro.invoke([
            _get_system_message(),
            HumanMessage(content=prompt),
        ])

        parsed = parse_llm_json(response.content)
        synth_data = parsed["data"]
        duration = (time.time() - start) * 1000

        contradictions = [
            f"{c['claim_a']} vs {c['claim_b']}"
            for c in synth_data.get("contradictions", [])
        ]

        step = ThinkingStep(
            step_id=step_id,
            type="synthesize",
            timestamp=datetime.now(timezone.utc).isoformat(),
            duration_ms=round(duration, 2),
            thinking=parsed["thinking"],
            action=parsed["action"],
            data=synth_data,
            tokens_used=_extract_tokens(response),
        )

        log.info(
            "node.synthesize_results.complete",
            final_confidence=synth_data.get("final_confidence", 0),
            sources_used=synth_data.get("sources_used", 0),
            contradictions=len(contradictions),
            duration_ms=round(duration, 2),
        )

        return {
            "synthesized_content": synth_data["answer"],
            "contradictions_found": contradictions,
            "final_confidence": synth_data["final_confidence"],
            "final_answer": synth_data["answer"],
            "citations": synth_data.get("citations", []),
            "caveats": synth_data.get("caveats", []),
            "should_stop": True,
            "thinking_log": [step],
        }

    except Exception as e:
        log.error("node.synthesize_results.error", error=str(e))
        duration = (time.time() - start) * 1000
        error_step = ThinkingStep(
            step_id=step_id,
            type="synthesize",
            timestamp=datetime.now(timezone.utc).isoformat(),
            duration_ms=round(duration, 2),
            thinking=f"Synthesis error: {str(e)}",
            action="Synthesis failed — returning raw results",
            data={"error": str(e)},
            tokens_used=0,
        )
        raw_titles = [r.get("title", "Unknown") for r in state.get("all_search_results", [])[:10]]
        fallback_answer = (
            f"Research synthesis encountered an error. "
            f"Raw sources found: {', '.join(raw_titles)}. "
            f"Please retry with a more specific query."
        )
        return {
            "synthesized_content": fallback_answer,
            "contradictions_found": [],
            "final_confidence": 0.0,
            "final_answer": fallback_answer,
            "citations": [],
            "caveats": ["Synthesis failed — raw results returned"],
            "should_stop": True,
            "thinking_log": [error_step],
            "error": str(e),
        }


# ═══════════════════════════════════════════════════════════════
# CONDITIONAL EDGE: should_continue
# ═══════════════════════════════════════════════════════════════

def should_continue(state: AgentState) -> str:
    """
    LangGraph conditional edge function.

    Determines the next node after evaluate_results:
      - "search"           → retry with a reformulated query
      - "synthesize"       → confidence threshold met, produce final answer
      - "force_synthesize" → max iterations reached, synthesize what we have
    """
    if state.get("should_stop"):
        return "synthesize"

    eval_result = state.get("latest_evaluation")
    if not eval_result:
        return "search"

    if eval_result.get("threshold_met", False):
        log.info("should_continue.threshold_met", confidence=eval_result.get("confidence"))
        return "synthesize"

    if state.get("current_iteration", 0) >= settings.max_iterations:
        log.info(
            "should_continue.max_iterations_reached",
            iteration=state["current_iteration"],
            max=settings.max_iterations,
        )
        return "force_synthesize"

    log.info(
        "should_continue.retrying",
        confidence=eval_result.get("confidence"),
        iteration=state.get("current_iteration"),
    )
    return "search"
