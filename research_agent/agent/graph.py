"""
LangGraph StateGraph definition for the NEXUS research agent.

Wires the five node functions into a directed graph with a conditional
loop (search → evaluate → retry OR synthesize). The compiled graph is
exported as `agent_graph` for use by the API layer.

Flow:
  plan → search → evaluate ─┬─→ synthesize ──→ END
                             ├─→ search (retry)
                             └─→ force_synthesize ──→ END
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langgraph.graph import StateGraph, END
from agent.state import AgentState
from agent.nodes import (
    plan_research,
    execute_search,
    evaluate_results,
    synthesize_results,
    should_continue,
)


def build_agent_graph() -> StateGraph:
    """
    Construct and compile the NEXUS agent graph.

    Returns:
        A compiled LangGraph StateGraph ready to .invoke() or .stream().
    """
    graph = StateGraph(AgentState)

    # ── Add all nodes ──
    graph.add_node("plan", plan_research)
    graph.add_node("search", execute_search)
    graph.add_node("evaluate", evaluate_results)
    graph.add_node("synthesize", synthesize_results)
    graph.add_node("force_synthesize", synthesize_results)  # same fn, safety stop

    # ── Entry point ──
    graph.set_entry_point("plan")

    # ── Fixed edges ──
    graph.add_edge("plan", "search")
    graph.add_edge("search", "evaluate")

    # ── Conditional edge: after evaluate ──
    graph.add_conditional_edges(
        "evaluate",
        should_continue,
        {
            "search": "search",
            "synthesize": "synthesize",
            "force_synthesize": "force_synthesize",
        },
    )

    # ── Terminal edges ──
    graph.add_edge("synthesize", END)
    graph.add_edge("force_synthesize", END)

    return graph.compile()


# Pre-compiled graph instance, used by routes
agent_graph = build_agent_graph()
