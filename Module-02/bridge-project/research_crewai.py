"""CrewAI bridge project.

This version uses a manager + researcher pattern. The researcher does the web
search and returns evidence. The manager tells the writer how to answer or
refuse.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from crewai import Agent, Crew, Process, Task
from crewai.tools import tool
from langchain_openai import ChatOpenAI

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


@tool("Search the web for a fact or claim")
def search_web(query: str) -> str:
    """Use the provided web search helper and return its result."""
    return web_search(query)


def run_question(question: str) -> str:
    researcher = Agent(
        role="Researcher",
        goal="Search for evidence and report exactly what you found.",
        backstory=(
            "You are a careful researcher. If the search returns no results or the search service "
            "is unavailable, you must say so plainly instead of inventing facts."
        ),
        tools=[search_web],
        llm=llm,
        verbose=True,
    )

    writer = Agent(
        role="Writer",
        goal="Answer or refuse using the evidence, never inventing facts.",
        backstory=(
            "You must not make up details. If the evidence is weak, insufficient, or missing, "
            "say that the claim could not be verified and finish with a NEXT SEARCH: <query> line."
        ),
        llm=llm,
        verbose=True,
    )

    manager = Agent(
        role="Manager",
        goal="Coordinate the researcher and writer to answer faithfully.",
        backstory=(
            "You are strict about evidence. The team may answer only when sources exist and are relevant. "
            "When evidence is missing, the proper output is a refusal with a NEXT SEARCH line."
        ),
        llm=llm,
        verbose=True,
    )

    research_task = Task(
        description=(
            "Search for reliable evidence for this claim: {question}. "
            "Use the search_web tool and report the exact result. "
            "If the result is NO_RESULTS or SEARCH_UNAVAILABLE, say that explicitly."
        ),
        expected_output="A short evidence report with the exact search result and any source URL(s) if present.",
        agent=researcher,
    )

    write_task = Task(
        description=(
            "Use only the evidence from the researcher. "
            "If there is enough evidence to answer, answer it with a source URL. "
            "If there is not enough evidence, refuse and end with a line like: NEXT SEARCH: <query>. "
            "Do not invent facts.\n\nClaim: {question}"
        ),
        expected_output="Either a concise answer with a source URL or a refusal with NEXT SEARCH.",
        agent=writer,
    )

    crew = Crew(
        agents=[researcher, writer, manager],
        tasks=[research_task, write_task],
        process=Process.hierarchical,
        manager_llm=llm,
        verbose=True,
    )

    result = crew.kickoff(inputs={"question": question})
    return str(result)


def main() -> int:
    question = " ".join(sys.argv[1:]).strip() or "Anthropic was founded by former OpenAI employees"
    print("=" * 70)
    print(f"QUESTION: {question}")
    print("=" * 70)
    print(run_question(question))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
