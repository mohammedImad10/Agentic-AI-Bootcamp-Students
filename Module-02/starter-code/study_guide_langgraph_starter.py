"""
Module 2 Phase 1 Mini-Project — LangGraph starter.

Build the same three-task Study Guide Agent in LangGraph and CrewAI.
Read M2-Phase1-Mini-Project.md before filling in the TODOs.

Run it with your own topic:
    python study_guide_langgraph_starter.py "temperature in language models"
"""

from __future__ import annotations

import os
import sys
from typing import TypedDict

from dotenv import find_dotenv, load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

for proxy_var in ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"]:
    os.environ.pop(proxy_var, None)

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

llm = ChatOpenAI(
    model="openai/gpt-4o-mini",
    temperature=0,
    base_url=os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    api_key=api_key,
)


class StudyGuideState(TypedDict):
    topic: str
    explanation: str
    example: str
    quiz: str


def fallback_explanation(topic: str) -> str:
    return (
        f"{topic} is a concept that helps people understand how a system or tool behaves. "
        "The explanation focuses on the core idea in plain language, without jargon or unnecessary detail."
    )


def fallback_example(topic: str, explanation: str) -> str:
    return (
        f"Practical example: imagine using {topic} in a small real-world workflow where the idea helps someone make a better decision. "
        f"Common misconception: people often assume {topic} is only about one narrow use case, when it is broader than that."
    )


def fallback_quiz(topic: str, explanation: str, example: str) -> str:
    return (
        "1. What is the main idea behind this topic?\n"
        "Answer: It is the core concept that makes the tool or system understandable.\n\n"
        "2. Why does the example matter?\n"
        "Answer: It shows how the concept applies in practice.\n\n"
        "3. What misconception should learners avoid?\n"
        "Answer: They should avoid thinking the topic is only relevant in one narrow situation."
    )


def call_model(prompt: str, *, kind: str) -> str:
    try:
        response = llm.invoke(prompt)
        return response.content.strip()
    except Exception:
        if kind == "explanation":
            return fallback_explanation(prompt.split("topic:", 1)[-1].strip() if "topic:" in prompt else "")
        if kind == "example":
            return fallback_example("", "")
        return fallback_quiz("", "", "")


def explain_topic(state: StudyGuideState) -> StudyGuideState:
    """Task 1: explain the topic in plain language."""
    prompt = (
        "You are a patient study-guide teacher. Explain the topic below in 2-3 plain-language sentences. "
        "Do not invent facts or statistics.\n\n"
        f"Topic: {state['topic']}"
    )
    state["explanation"] = call_model(prompt, kind="explanation")
    return state


def create_example(state: StudyGuideState) -> StudyGuideState:
    """Task 2: use the explanation to create an example and misconception."""
    prompt = (
        "Based on the explanation below, give one practical example and one common misconception. "
        "Make it clear which part is the example and which part is the misconception.\n\n"
        f"Topic: {state['topic']}\nExplanation: {state['explanation']}"
    )
    state["example"] = call_model(prompt, kind="example")
    return state


def create_quiz(state: StudyGuideState) -> StudyGuideState:
    """Task 3: use earlier state to create three questions and answers."""
    prompt = (
        "Create exactly three questions and an answer key for the study guide below. "
        "Use the topic, explanation, and example to make the quiz accurate and useful.\n\n"
        f"Topic: {state['topic']}\nExplanation: {state['explanation']}\nExample: {state['example']}"
    )
    state["quiz"] = call_model(prompt, kind="quiz")
    return state


def build_graph():
    graph = StateGraph(StudyGuideState)
    graph.add_node("explain_topic", explain_topic)
    graph.add_node("create_example", create_example)
    graph.add_node("create_quiz", create_quiz)
    graph.add_edge(START, "explain_topic")
    graph.add_edge("explain_topic", "create_example")
    graph.add_edge("create_example", "create_quiz")
    graph.add_edge("create_quiz", END)
    return graph.compile()


def run_study_guide(topic: str) -> StudyGuideState:
    app = build_graph()
    initial_state: StudyGuideState = {
        "topic": topic,
        "explanation": "",
        "example": "",
        "quiz": "",
    }
    return app.invoke(initial_state)


if __name__ == "__main__":
    topic = " ".join(sys.argv[1:]).strip() or "Model Context Protocol"
    result = run_study_guide(topic)

    print(f"# Study Guide: {result['topic']}\n")
    print("## Explanation\n", result["explanation"])
    print("\n## Example and misconception\n", result["example"])
    print("\n## Quiz\n", result["quiz"])
