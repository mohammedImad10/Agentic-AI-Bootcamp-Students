"""
Exercise 1 -- the honest comparison: ONE agent doing all three jobs.

Run this after the team works, on the same sample, and compare the two cost
cards. Then ask the only question that matters:

    Was the team worth it -- for THIS job?

For eight lines of code the answer is often "no". A team pays off when the
jobs need different instructions, different tools or permissions, an
independent check, or work that can run at the same time. Not before.

Run:
    python solo_agent.py              # same 'orders' sample as the team
    python solo_agent.py split_bill
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "shared"))

import setup_env  # noqa: E402  ALWAYS FIRST
from meter import Meter, banner, indent  # noqa: E402
from samples import check_planted, pick_sample  # noqa: E402

from crewai import Agent, Crew, Process, Task  # noqa: E402

one_agent = Agent(
    role="Full-Stack Code Reviewer",
    goal="Review, fix and explain a piece of Python code",
    backstory="You do the whole job yourself: find the problems, fix them, explain the fix.",
    llm=setup_env.crew_llm(),
    verbose=False,
    max_iter=2,
)

everything = Task(
    description=(
        "Here is some Python code:\n\n{code}\n\n"
        "1. List at most 3 problems, most serious first, one line each.\n"
        "2. Give the complete fixed code.\n"
        "3. Explain the fix to a junior developer in exactly 3 short bullets."
    ),
    expected_output="Three sections: PROBLEMS, FIXED CODE, EXPLANATION.",
    agent=one_agent,
)

crew = Crew(agents=[one_agent], tasks=[everything], process=Process.sequential,
            verbose=False, tracing=False)


def main() -> int:
    sample_name, code = pick_sample(sys.argv)
    meter = Meter()
    print(banner(f"ONE AGENT, ALL THREE JOBS  ·  reviewing '{sample_name}'"))
    result = crew.kickoff(inputs={"code": code})
    meter.record_crew(result)
    print(indent(result.raw))
    print("\n" + check_planted(sample_name, result.raw))
    print("\n" + meter.card(agents=1, model=setup_env.MODEL,
                            note="compare with the team's card from team_solution.py"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
