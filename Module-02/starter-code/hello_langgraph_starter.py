"""
Module 2 Lab — STARTER (LangGraph "hello agent")
Goal: a tiny graph that, given a topic, returns a one-sentence definition.

Fill in the TODOs. Keep it minimal — the point is to FEEL explicit control flow.
Set your key in .env (OPENROUTER_API_KEY=sk-or-...) and load it with python-dotenv.
"""

import os
from typing import TypedDict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

load_dotenv()


class State(TypedDict):
    topic: str
    definition: str


llm = ChatOpenAI(
    model="openai/gpt-4o-mini",
    temperature=0,
    base_url=os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    api_key=os.environ["OPENROUTER_API_KEY"],
)


def define(state: State) -> State:
    """Node: produce a one-sentence definition of state['topic']."""
    prompt = f"Define '{state['topic']}' in exactly one sentence."
    response = llm.invoke(prompt)
    state["definition"] = response.content.strip()
    return state


def format_output(state: State) -> State:
    """Node (Step 4): wrap the definition, e.g. prefix 'Definition: '."""
    state["definition"] = f"Definition: {state['definition']}"
    return state


def build_graph():
    g = StateGraph(State)
    g.add_node("define", define)
    g.add_node("format_output", format_output)
    g.set_entry_point("define")
    g.add_edge("define", "format_output")
    g.add_edge("format_output", END)
    return g.compile()


if __name__ == "__main__":
    app = build_graph()
    result = app.invoke({"topic": "agentic AI", "definition": ""})
    print(result["definition"])
