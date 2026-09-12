from __future__ import annotations

import os
import sys
from typing import Literal, Optional, TypedDict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from registry_tools import (
    LOOKUP_UNAVAILABLE,
    NO_RECORDS,
    gleif_lookup,
    sanctions_screen,
)
from search_tools import web_search

load_dotenv()

# Sanctions screening is mandatory and free; this only rations GLEIF/web lookups.
MAX_LOOKUPS = 9
MAX_SCREEN_STEPS = 4
SANCTIONS_THRESHOLD = 0.90

BUDGET = {"used": 0}

llm = ChatOpenAI(
    model="openai/gpt-4o-mini",
    temperature=0,
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY", ""),
)


# ===========================================================================
# 1 - SCHEMAS
# ===========================================================================

class Supplier(BaseModel):
    name: str
    annual_value_hint: str = Field(default="", description="Any value/size cue from the email, if present.")
    jurisdiction: str = Field(default="", description="Country/region mentioned for this supplier, if any.")


class Plan(BaseModel):
    """Order suppliers so the budget is spent where ambiguity is highest."""
    suppliers: list[Supplier]
    rationale: str = Field(description="Why this order - which ones are worth the budget first.")


class ScreenAction(BaseModel):
    """One ReAct move while screening a single supplier."""
    tool: Literal["gleif_lookup", "web_search", "enough_evidence"]
    query: Optional[str] = Field(default=None, description="Query text, when tool is gleif_lookup or web_search.")


class Verdict(BaseModel):
    supplier: str
    verdict: Literal["APPROVE", "CONDITIONS", "REJECT", "INSUFFICIENT"]
    reason: str = Field(description="Why. In language Rana can repeat to Procurement.")
    required_action: str = Field(description="The exact next step Rana should take.")


# ===========================================================================
# 2 - STATE
# ===========================================================================

class State(TypedDict):
    request: str
    queue: list[Supplier]
    verdicts: list[dict]
    skipped: list[str]
    memo: str
    active_supplier: Optional[Supplier]
    active_evidence: list[str]


def spend(label: str) -> bool:
    if BUDGET["used"] >= MAX_LOOKUPS:
        return False
    BUDGET["used"] += 1
    print(f"  [{BUDGET['used']:2}/{MAX_LOOKUPS}] {label}")
    return True


# ===========================================================================
# 3 - NODES
# ===========================================================================

def triage(state: State) -> State:
    """LLM reads the raw request email and plans a spend-aware order."""
    planner_llm = llm.with_structured_output(Plan)
    prompt = (
        "You are triaging suppliers for a payment run with a strict budget of "
        f"{MAX_LOOKUPS} expensive identity-verification lookups across all suppliers "
        "(sanctions screening is separate and unlimited). Read the email below, extract "
        "every supplier, and order them so the budget is spent on the ones most likely "
        "to be ambiguous (unfamiliar or generic names, unclear jurisdiction) before the "
        "ones that are obviously low-risk or low-value.\n\n"
        f"EMAIL:\n{state['request']}"
    )
    plan = planner_llm.invoke(prompt)
    state["queue"] = plan.suppliers
    state["verdicts"] = []
    state["skipped"] = []
    state["memo"] = ""
    state["active_supplier"] = None
    state["active_evidence"] = []
    BUDGET["used"] = 0
    print(f"  triage rationale: {plan.rationale}")
    return state


def screen(state: State) -> State:
    """ReAct loop: hand one supplier to the model and let it pick its own tools."""
    supplier = state["queue"][0]
    state["active_supplier"] = supplier

    sanctions_report = sanctions_screen(supplier.name, top=5)
    evidence: list[str] = [f"sanctions_screen result:\n{sanctions_report}"]

    action_llm = llm.with_structured_output(ScreenAction)
    for _ in range(MAX_SCREEN_STEPS):
        prompt = (
            f"You are verifying the legal identity of the supplier '{supplier.name}' "
            "before a payment can be released. Decide the next tool to call, or say "
            "you have enough evidence to hand off for a decision.\n\n"
            "Tools:\n"
            "  gleif_lookup(query) - the global LEI legal-entity register\n"
            "  web_search(query) - general web search, useful only when GLEIF has no record\n"
            "  enough_evidence - stop gathering, you can already decide\n\n"
            f"EVIDENCE SO FAR:\n{chr(10).join(evidence)}"
        )
        action = action_llm.invoke(prompt)

        if action.tool == "enough_evidence":
            break

        if not spend(f"{action.tool}({supplier.name})"):
            evidence.append("BUDGET EXHAUSTED: no further lookups available.")
            state["skipped"].append(supplier.name)
            state["active_supplier"] = None
            state["queue"] = state["queue"][1:]
            return state

        query = action.query or supplier.name
        result = gleif_lookup(query) if action.tool == "gleif_lookup" else web_search(query)
        evidence.append(f"{action.tool}('{query}') result:\n{result}")

        if result in (NO_RECORDS, LOOKUP_UNAVAILABLE) and action.tool == "gleif_lookup":
            continue

    state["active_evidence"] = evidence
    return state


def decide(state: State) -> State:
    """LLM turns the gathered evidence for one supplier into a verdict."""
    supplier = state["active_supplier"]
    verdict_llm = llm.with_structured_output(Verdict)
    evidence_text = "\n\n".join(state["active_evidence"])
    prompt = (
        f"Decide the verdict for supplier '{supplier.name}' using ONLY the evidence below. "
        "Never invent a fact that is not in the evidence.\n\n"
        "Four verdicts:\n"
        "  APPROVE - real, current, clean: release payment\n"
        "  CONDITIONS - pay only after something specific; name exactly what is missing\n"
        "  REJECT - do not pay; give one sentence Rana can repeat to Procurement\n"
        "  INSUFFICIENT - could not establish identity; say precisely what would settle it\n\n"
        "Traps to avoid:\n"
        f"  - A sanctions similarity score at or above {SANCTIONS_THRESHOLD:.2f} against the "
        "target company is a REJECT; scores below that on a generic shared word are noise, not a match. "
        "Read every score in the report, not just the first line - the true match may not be first.\n"
        "  - If GLEIF returns several different legal entities and none is named exactly like "
        "the supplier, that is CONDITIONS (ask which one), not an automatic APPROVE of the first result.\n"
        "  - NO_RECORDS from GLEIF does not mean the company is fake - check whether web search "
        "found independent evidence before choosing REJECT vs CONDITIONS vs INSUFFICIENT.\n"
        "  - A LAPSED or RETIRED registration status on the exact-match entity is CONDITIONS, not APPROVE.\n\n"
        f"EVIDENCE:\n{evidence_text}"
    )
    verdict = verdict_llm.invoke(prompt)
    state["verdicts"].append(verdict.model_dump())
    state["active_supplier"] = None
    state["queue"] = state["queue"][1:]
    return state


def after_screen(state: State) -> str:
    """Skip straight to routing when screen() already dequeued a budget-exhausted supplier."""
    return "route" if state["active_supplier"] is None else "decide"


def budget_left(state: State) -> str:
    if not state["queue"]:
        return "memo"
    if BUDGET["used"] >= MAX_LOOKUPS:
        return "memo"
    return "screen"


def write_memo(state: State) -> State:
    lines = [
        f"SUPPLIER REVIEW - Thursday payment run - "
        f"{len(state['verdicts']) + len(state['skipped'])} suppliers - {BUDGET['used']} lookups used",
        "",
    ]

    for item in state["verdicts"]:
        lines.extend([
            f"  {item['verdict']:<13} {item['supplier']}",
            f"                {item['reason']}",
            f"                -> Rana: {item['required_action']}",
            "",
        ])

    for name in state["skipped"]:
        lines.extend([
            "  NOT CHECKED (budget)",
            f"                {name} - remaining lookups were spent on higher-ambiguity suppliers.",
            "                Residual risk: accepted, not assessed.",
            "",
        ])

    state["memo"] = "\n".join(lines)
    return state


def build_graph():
    g = StateGraph(State)
    g.add_node("triage", triage)
    g.add_node("screen", screen)
    g.add_node("decide", decide)
    g.add_node("write_memo", write_memo)
    g.set_entry_point("triage")
    g.add_edge("triage", "screen")
    g.add_conditional_edges("screen", after_screen, {"decide": "decide", "route": "screen"})
    g.add_conditional_edges("decide", budget_left, {"screen": "screen", "memo": "write_memo"})
    g.add_edge("write_memo", END)
    return g


if __name__ == "__main__":
    state: State = {
        "request": open("REQUEST.md", "r", encoding="utf-8").read(),
        "queue": [],
        "verdicts": [],
        "skipped": [],
        "memo": "",
        "active_supplier": None,
        "active_evidence": [],
    }
    graph = build_graph().compile()
    final_state = graph.invoke(state)

    with open("MEMO.md", "w", encoding="utf-8") as f:
        f.write(final_state["memo"] + "\n")

    print(f"\nCompleted: {BUDGET['used']} lookups used")
    print("Wrote MEMO.md")
    print("\n--- memo head ---")
    print("\n".join(final_state["memo"].splitlines()[:12]))
