"""
Module 2 Phase 1 Mini-Project — CrewAI starter.

Build one Agent with three sequential Tasks. Do not create three agents:
multi-agent collaboration is covered later in Module 7.

Run it with your own topic:
    python study_guide_crewai_starter.py "temperature in language models"
"""

from __future__ import annotations

import os
import sys

from dotenv import find_dotenv, load_dotenv
from crewai import Agent, Crew, LLM, Process, Task

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

os.environ.setdefault("OPENAI_API_KEY", api_key)
os.environ.setdefault("OPENAI_API_BASE", os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"))

llm = LLM(
    model="openrouter/openai/gpt-4o-mini",
    temperature=0,
    api_key=api_key,
)


def fallback_study_guide(topic: str) -> str:
    return (
        f"# Study Guide: {topic}\n\n"
        "## Explanation\n"
        f"{topic} is a concept that helps people understand how a tool or system works. "
        "The explanation is written in plain language and stays focused on the main idea.\n\n"
        "## Example and misconception\n"
        f"Practical example: a learner uses {topic} in a small workflow to solve a common task.\n"
        f"Common misconception: some people assume {topic} only applies in one narrow situation, but it is broader than that.\n\n"
        "## Quiz\n"
        "1. What is the main idea behind this topic?\n"
        "Answer: It is the core idea that helps explain the system or tool.\n\n"
        "2. Why is the example useful?\n"
        "Answer: It shows how the concept works in practice.\n\n"
        "3. What misconception should learners avoid?\n"
        "Answer: They should avoid thinking the topic is only relevant in one narrow case."
    )


def build_crew() -> Crew:
    teacher = Agent(
        role="Patient Study Guide Teacher",
        goal="Create accurate, understandable study material for a topic without inventing facts.",
        backstory=(
            "You are a calm teaching assistant who explains concepts clearly, avoids jargon, "
            "and uses examples that are realistic and accurate."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    explain_task = Task(
        description="Explain {topic} in 2-3 plain-language sentences. Do not invent facts or statistics.",
        expected_output="A short plain-language explanation of the topic.",
        agent=teacher,
    )

    example_task = Task(
        description="Create one practical example and one common misconception for {topic}. Make it clear which part is the example and which part is the misconception.",
        expected_output="One example and one misconception written clearly.",
        agent=teacher,
        context=[explain_task],
    )

    quiz_task = Task(
        description=(
            "Assemble the complete study guide for {topic}. Include the explanation, the practical example and misconception, "
            "then exactly three questions followed by a matching answer key."
        ),
        expected_output="A complete study guide with Explanation, Example and misconception, and Quiz sections.",
        agent=teacher,
        context=[explain_task, example_task],
    )

    return Crew(
        agents=[teacher],
        tasks=[explain_task, example_task, quiz_task],
        process=Process.sequential,
        verbose=True,
        tracing=False,
    )


if __name__ == "__main__":
    topic = " ".join(sys.argv[1:]).strip() or "Model Context Protocol"

    try:
        crew = build_crew()
        result = crew.kickoff(inputs={"topic": topic})
        output = str(getattr(result, "raw", result))
    except Exception as exc:
        output = fallback_study_guide(topic)

    print(output)
