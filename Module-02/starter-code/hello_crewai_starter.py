"""
Module 2 Lab — STARTER (CrewAI "hello agent")
Goal: one role + one task that, given a topic, returns a one-sentence definition.

Fill in the TODOs. Notice you DESCRIBE roles/tasks — you don't wire nodes/edges.
Set your key in .env (OPENROUTER_API_KEY=sk-or-...).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

try:
    from crewai import Agent, Crew, Process, Task
except ImportError as exc:  # pragma: no cover - runtime guard
    raise SystemExit(
        "CrewAI is not installed. Install the Module 2 dependencies first: "
        "pip install -r requirements.txt"
    ) from exc


def build_crew() -> Crew:
    api_key = os.getenv("OPENROUTER_API_KEY")
    base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

    if not api_key:
        raise ValueError(
            "OPENROUTER_API_KEY was not found. Make sure your repo-root .env contains it."
        )

    os.environ.setdefault("OPENAI_API_KEY", api_key)
    os.environ.setdefault("OPENAI_API_BASE", base_url)

    definer = Agent(
        role="Concise Encyclopedia",
        goal="Define topics in exactly one sentence.",
        backstory=(
            "You are a concise encyclopedia writer who explains concepts clearly "
            "and briefly."
        ),
        verbose=True,
        allow_delegation=False,
        llm="openrouter/openai/gpt-4o-mini",
    )

    define_task = Task(
        description="Define {topic} in exactly one sentence.",
        expected_output="A single-sentence definition.",
        agent=definer,
    )

    return Crew(
        agents=[definer],
        tasks=[define_task],
        process=Process.sequential,
        verbose=True,
    )


if __name__ == "__main__":
    crew = build_crew()
    result = crew.kickoff(inputs={"topic": "agentic AI"})
    print(getattr(result, "raw", result))
