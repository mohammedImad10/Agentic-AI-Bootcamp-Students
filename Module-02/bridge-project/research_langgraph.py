"""
Module 2 Bridge Project - LangGraph

Build an agent that searches the web, decides whether what it found is good
enough, and then does ONE OF TWO different things.

Run:
    python research_langgraph.py "Anthropic was founded by ex-OpenAI staff"
    python research_langgraph.py "the flurbotron 9000 was released in 2019"
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Literal, TypedDict

from dotenv import find_dotenv, load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

for proxy_var in ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"]:
    os.environ.pop(proxy_var, None)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from search_tools import NO_RESULTS, SEARCH_UNAVAILABLE, web_search  # noqa: E402

load_dotenv()
load_dotenv(find_dotenv(usecwd=True))

api_key = os.environ.get("OPENROUTER_API_KEY")
base_url = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
if not api_key:
    raise RuntimeError(
        "OPENROUTER_API_KEY not found.\n"
        "Create a file named .env in the project folder containing:\n"
        "    OPENROUTER_API_KEY=sk-or-...\n"
        "then run this script again."
    )

llm = ChatOpenAI(
    model="openai/gpt-4o-mini",
    temperature=0,
    base_url=base_url,
    api_key=api_key,
)


class DeskState(TypedDict):
    question: str
    query: str
    evidence: str
    verdict: str
    reasoning: str
    output: str
    route_taken: str


def plan_query(state: DeskState) -> DeskState:
    """Turn the question into one short search query."""
    prompt = (
        "Turn the user question into one short web-search query. "
        "Return only the query and nothing else.\n\n"
        f"Question: {state['question']}"
    )
    response = llm.invoke(prompt)
    text = (response.content or "").strip()
    query = ""
    for line in text.splitlines():
        candidate = line.strip().strip('"\'')
        if candidate:
            query = candidate
            break
    if not query:
        query = state['question']
    state["query"] = query
    return state


def run_search(state: DeskState) -> DeskState:
    """Use the built-in search tool; no model call here."""
    state["evidence"] = web_search(state["query"])
    return state


def assess(state: DeskState) -> DeskState:
    """Decide whether the evidence is enough to answer honestly."""
    if state["evidence"] == NO_RESULTS:
        state["verdict"] = "NOT_ENOUGH"
        state["reasoning"] = "The search returned no relevant evidence for the question."
        return state
    if state["evidence"] == SEARCH_UNAVAILABLE:
        state["verdict"] = "NOT_ENOUGH"
        state["reasoning"] = "The search service was unavailable, so the evidence could not be checked."
        return state

    prompt = (
        "Decide whether the evidence is enough to answer the question honestly. "
        "Return 1-3 short bullet points, and on the final line write exactly ENOUGH or NOT_ENOUGH.\n\n"
        f"Question: {state['question']}\n\nEvidence:\n{state['evidence']}"
    )
    response = llm.invoke(prompt)
    raw = (response.content or "").strip()
    state["reasoning"] = raw
    state["verdict"] = read_verdict(raw)
    return state


def read_verdict(raw: str) -> str:
    """Read the last meaningful verdict from the model output."""
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    if not lines:
        return "NOT_ENOUGH"
    for line in reversed(lines):
        upper = line.upper()
        if "NOT_ENOUGH" in upper:
            return "NOT_ENOUGH"
        if "ENOUGH" in upper:
            return "ENOUGH"
    return "NOT_ENOUGH"


def choose_next(state: DeskState) -> Literal["write_answer", "report_gap"]:
    """Route to the answer branch or refusal branch."""
    return "write_answer" if state["verdict"] == "ENOUGH" else "report_gap"


def write_answer(state: DeskState) -> DeskState:
    """Answer using only the evidence and cite a source URL."""
    prompt = (
        "Use only the evidence below to answer the question. Do not invent anything. "
        "Cite at least one source URL from the evidence. If part of the question is not covered, say so. "
        "Keep the answer under 180 words.\n\n"
        f"Question: {state['question']}\n\nEvidence:\n{state['evidence']}"
    )
    output = llm.invoke(prompt).content.strip()
    state["output"] = output
    state["route_taken"] = "answered"
    return state


def report_gap(state: DeskState) -> DeskState:
    """Refuse to answer when the evidence is insufficient."""
    prompt = (
        "The evidence is not enough to answer this question honestly. Write a short refusal: "
        "1) say plainly that it could not be verified, 2) list one or two things that are missing, "
        "3) finish with exactly this final line format: NEXT SEARCH: <one query>.\n\n"
        f"Question: {state['question']}\n\nEvidence:\n{state['evidence']}"
    )
    output = llm.invoke(prompt).content.strip()
    state["output"] = output
    state["route_taken"] = "gap_reported"
    return state


def build_graph():
    graph = StateGraph(DeskState)
    graph.add_node("plan_query", plan_query)
    graph.add_node("run_search", run_search)
    graph.add_node("assess", assess)
    graph.add_node("write_answer", write_answer)
    graph.add_node("report_gap", report_gap)

    graph.set_entry_point("plan_query")
    graph.add_edge("plan_query", "run_search")
    graph.add_edge("run_search", "assess")
    graph.add_conditional_edges(
        "assess",
        choose_next,
        {
            "write_answer": "write_answer",
            "report_gap": "report_gap",
        },
    )
    graph.add_edge("write_answer", END)
    graph.add_edge("report_gap", END)
    return graph.compile()


def run(question: str) -> DeskState:
    return build_graph().invoke({
        "question": question,
        "query": "",
        "evidence": "",
        "verdict": "",
        "reasoning": "",
        "output": "",
        "route_taken": "",
    })


def main() -> int:
    question = " ".join(sys.argv[1:]).strip() or "Anthropic was founded by former OpenAI employees"
    result = run(question)

    print("=" * 70)
    print(f"QUESTION : {result['question']}")
    print("=" * 70)
    print(f"\n[1] SEARCH QUERY\n{result['query']}")
    print(f"\n[2] EVIDENCE ({len(result['evidence'])} chars)")
    print(result["evidence"][:700])
    print(f"\n[3] ASSESSMENT\n{result['reasoning']}")
    print("\n" + "=" * 70)
    print(f"VERDICT : {result['verdict']}")
    print(f"ROUTE   : {result['route_taken'].upper()}")
    print("=" * 70)
    print(result["output"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
