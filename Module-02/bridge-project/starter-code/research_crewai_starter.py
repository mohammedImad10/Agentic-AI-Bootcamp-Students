"""
Module 2 Bridge Project - CrewAI STARTER (hierarchical)

Same job as the LangGraph version. Build that one FIRST, then come back here.

WHAT IS DIFFERENT
    In LangGraph you drew the branch yourself, in one line you could point
    at. A hierarchical crew has no such line. Instead you hire a MANAGER and
    let it decide who works, in what order, and when the job is done.

    You are trading a decision you can READ for a decision you DELEGATE.

    Run both versions on the nonsense claim afterwards and watch carefully.
    In LangGraph, refusing is a code path - report_gap physically cannot
    produce an answer. Here, refusing is an instruction in a backstory. You
    are asking the manager nicely.

    Whether it listens is the most interesting result in this project, and
    it goes in your README either way.

Run:
    python research_crewai_starter.py "Anthropic was founded by ex-OpenAI staff"
    python research_crewai_starter.py "the flurbotron 9000 was released in 2019"
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# CrewAI asks about execution traces on the first run in a new folder and
# blocks for 20 seconds waiting for an answer. This stops that.
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")

from crewai import Agent, Crew, LLM, Process, Task  # noqa: E402
from crewai.tools import tool  # noqa: E402
from dotenv import find_dotenv, load_dotenv  # noqa: E402

try:
    from crewai.events.listeners.tracing.utils import mark_first_execution_done

    mark_first_execution_done()
except Exception:      # different CrewAI version - the prompt times out anyway
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from search_tools import web_search  # noqa: E402

load_dotenv()
load_dotenv(find_dotenv(usecwd=True))

api_key = os.environ.get("OPENROUTER_API_KEY")
if not api_key:
    raise RuntimeError(
        "OPENROUTER_API_KEY not found.\n"
        "Create a file named .env in the project folder containing:\n"
        "    OPENROUTER_API_KEY=sk-or-...\n"
        "then run this script again."
    )


llm = LLM(
    model="openrouter/openai/gpt-4o-mini",
    temperature=0,
    api_key=api_key,
)


# ---------------------------------------------------------------------------
# THE TOOL
# ---------------------------------------------------------------------------
# In LangGraph the tool was a plain function call inside a node - YOU decided
# when it ran. Here you hand the tool to an agent and the agent decides.
@tool("Web Search")
def search_web(query: str) -> str:
    """Search the web for the given query and return factual findings with source URLs. The tool may return a numbered list of evidence, or the exact text NO_RESULTS if nothing relevant was found, or SEARCH_UNAVAILABLE if the search service could not run. Use the returned evidence directly and do not invent missing facts."""
    return web_search(query)


def build_crew() -> Crew:
    researcher = Agent(
        role="Research Analyst",
        goal="Find evidence for the user question using the web search tool and report the exact results with source URLs.",
        backstory="You are a careful researcher. You report what the search actually returned, keep the source URLs, and say plainly when the result is NO_RESULTS or SEARCH_UNAVAILABLE rather than guessing from memory.",
        tools=[search_web],
        llm=llm,
        verbose=True,
        max_iter=4,
    )

    writer = Agent(
        role="Evidence Writer",
        goal="Answer only when the evidence supports the claim; otherwise say the claim could not be verified.",
        backstory="You prefer an honest statement about missing evidence over a confident but unsupported answer. You cite sources and keep the wording brief.",
        llm=llm,
        verbose=True,
        max_iter=4,
    )

    # -----------------------------------------------------------------------
    # THE TASKS
    # -----------------------------------------------------------------------
    research_task = Task(
        description="Use the Web Search tool to find evidence about {question}. Report the exact findings and include source URLs. If the tool returns NO_RESULTS or SEARCH_UNAVAILABLE, say that plainly and do not invent missing facts.",
        expected_output="A factual summary of the search results with source URLs, or an explicit statement that the tool returned NO_RESULTS or SEARCH_UNAVAILABLE.",
    )

    write_task = Task(
        description="Use the evidence from the research step to either answer the question in under 180 words with at least one source URL, or say that it could not be verified and end with exactly: NEXT SEARCH: <one query>. Begin with either VERDICT: ANSWERED or VERDICT: COULD NOT VERIFY.",
        expected_output="Either a short answer with a source URL or a refusal with a NEXT SEARCH line.",
    )

    return Crew(
        agents=[researcher, writer],
        tasks=[research_task, write_task],
        process=Process.hierarchical,
        manager_llm=llm,
        verbose=True,
        tracing=False,
    )


def main() -> int:
    question = " ".join(sys.argv[1:]).strip() or \
        "Anthropic was founded by former OpenAI employees"

    result = str(build_crew().kickoff(inputs={"question": question}))

    print("\n" + "=" * 70)
    print(f"QUESTION : {question}")
    print("=" * 70)
    print(result)

    route = "answered" if "VERDICT: COULD NOT VERIFY" not in result.upper() else "gap_reported"

    print("\n" + "=" * 70)
    print(f"ROUTE : {route}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
