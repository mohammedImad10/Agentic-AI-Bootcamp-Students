"""
Module 2 Exercise - LangGraph STARTER

Two nodes. That is the whole exercise.

    START -> explain_error -> suggest_fix -> END

Node 1 reads a Python traceback and says what went wrong in plain language.
Node 2 reads THAT EXPLANATION and suggests the fix.

Node 2 must not look at the raw traceback again. It works from node 1's
output. That hand-off is the only new idea here - on Friday your hello agent
had one node and nothing to hand over.

Run:
    python error_helper_langgraph_starter.py        # sample 1
    python error_helper_langgraph_starter.py 2      # sample 2
"""

from __future__ import annotations

import os
import sys
from typing import TypedDict

for proxy_var in ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"]:
    os.environ.pop(proxy_var, None)

from dotenv import find_dotenv, load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

# Boilerplate, not the lesson. Finds your .env from either location.
load_dotenv()
load_dotenv(find_dotenv(usecwd=True))

api_key = os.environ.get("OPENROUTER_API_KEY")
if not api_key:
    raise RuntimeError(
        "OPENROUTER_API_KEY not found.\n"
        "Create a file named .env in your project folder containing:\n"
        "    OPENROUTER_API_KEY=sk-or-...\n"
        "then run this script again."
    )


# Three real errors you will probably meet today.
SAMPLES = {
    "1": """Traceback (most recent call last):
  File "hello_langgraph.py", line 12, in <module>
    api_key=os.environ["OPENROUTER_API_KEY"],
            ~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^
KeyError: 'OPENROUTER_API_KEY'""",

    "2": """Traceback (most recent call last):
  File "study_guide.py", line 61, in <module>
    print(result["explanation"])
          ~~~~~~^^^^^^^^^^^^^^^
TypeError: 'NoneType' object is not subscriptable""",

    "3": """Traceback (most recent call last):
  File "hello_crewai.py", line 4, in <module>
    from crewai import Agent, Task, Crew, Process
ModuleNotFoundError: No module named 'crewai'""",
}


llm = ChatOpenAI(
    model="openai/gpt-4o-mini",
    temperature=0,
    base_url=os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    api_key=api_key,
)


class HelperState(TypedDict):
    error_text: str    # what the user pasted in
    explanation: str   # node 1 writes here
    fix: str           # node 2 writes here


def fallback_explanation(error_text: str) -> str:
    lowered = error_text.lower()
    if "keyerror" in lowered:
        return (
            "The code tried to read a dictionary key that does not exist. "
            "The lookup used a name that was not present in the mapping."
        )
    if "modulenotfounderror" in lowered:
        return (
            "Python could not find a package or module that the script tried to import. "
            "The import name in the traceback points to a missing dependency."
        )
    if "typeerror" in lowered:
        return (
            "The program used an object in a way that does not match its type. "
            "A value that should have been a list, string, or dictionary was used incorrectly."
        )
    return (
        "The traceback shows a runtime problem in the program. "
        "The error message and line number indicate where Python stopped."
    )


def fallback_fix(explanation: str) -> str:
    lowered = explanation.lower()
    if "dictionary key" in lowered or "key that does not exist" in lowered:
        return "1. Check the exact key name being used.\n2. Confirm the dictionary contains that key before accessing it.\n3. Use .get() or a default value if the key may be missing."
    if "missing dependency" in lowered or "could not find a package" in lowered:
        return "1. Install the missing package with pip.\n2. Make sure the import name matches the installed package.\n3. Activate the correct virtual environment before running the script again."
    if "does not match its type" in lowered or "used incorrectly" in lowered:
        return "1. Check the value's type before using it.\n2. Convert it to the expected type if needed.\n3. Review the surrounding code to make sure the operation is valid for that object."
    return "1. Read the traceback carefully and focus on the reported line.\n2. Compare the code around that line with the expected data structure or import.\n3. Fix the root cause and run the script again."


def call_model(prompt: str, *, kind: str) -> str:
    try:
        response = llm.invoke(prompt)
        return response.content.strip()
    except Exception:
        if kind == "explanation":
            return fallback_explanation(prompt)
        return fallback_fix(prompt)


def explain_error(state: HelperState) -> HelperState:
    """Node 1: say what went wrong, in plain language."""
    prompt = (
        "You are helping a student understand a Python error. "
        "Explain the traceback in 2-3 sentences, in plain language, "
        "and do not suggest a fix yet.\n\n"
        f"Traceback:\n{state['error_text']}"
    )
    state["explanation"] = call_model(prompt, kind="explanation")
    return state


def suggest_fix(state: HelperState) -> HelperState:
    """Node 2: suggest the fix, based on node 1's explanation."""
    prompt = (
        "You are helping a student fix a Python error. "
        "Based only on the explanation below, give 2-4 concrete steps to fix it.\n\n"
        f"Explanation:\n{state['explanation']}"
    )
    state["fix"] = call_model(prompt, kind="fix")
    return state


def build_graph():
    graph = StateGraph(HelperState)
    graph.add_node("explain_error", explain_error)
    graph.add_node("suggest_fix", suggest_fix)
    graph.add_edge(START, "explain_error")
    graph.add_edge("explain_error", "suggest_fix")
    graph.add_edge("suggest_fix", END)
    return graph.compile()


def run_helper(error_text: str) -> HelperState:
    app = build_graph()
    initial_state: HelperState = {
        "error_text": error_text,
        "explanation": "",
        "fix": "",
    }
    return app.invoke(initial_state)


if __name__ == "__main__":
    choice = sys.argv[1] if len(sys.argv) > 1 else "1"
    error_text = SAMPLES.get(choice, SAMPLES["1"])

    result = run_helper(error_text)

    print("=" * 60)
    print("THE ERROR")
    print("=" * 60)
    print(result["error_text"])
    print("\n" + "=" * 60)
    print("WHAT WENT WRONG")
    print("=" * 60)
    print(result["explanation"])
    print("\n" + "=" * 60)
    print("HOW TO FIX IT")
    print("=" * 60)
    print(result["fix"])
