"""
Exercise 1 -- THE TEAM  (SOLUTION)
Agents share information by PASSING A NOTE.

    Reviewer ──note──▶ Fixer ──note──▶ Teacher

Three agents. One job each. Each one sees only the notes it is handed.

    Reviewer   finds the problems        (never fixes anything)
    Fixer      fixes exactly those       (sees the code + the Reviewer's note)
    Teacher    explains it to a junior   (sees the Reviewer's note + the fix)

In CrewAI the note is `context=[...]`: the list of earlier tasks whose
output this task is allowed to read. Context engineering decides what goes
into ONE agent's context. A team is the same idea, split: each agent's
context holds only what its own job needs.

Run:
    python team_solution.py              # reviews the 'orders' sample
    python team_solution.py split_bill   # a different piece of code
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "shared"))

import setup_env  # noqa: E402  ALWAYS FIRST: key, UTF-8, silences CrewAI's first-run question
from meter import Meter, banner, indent  # noqa: E402
from samples import check_planted, pick_sample  # noqa: E402

from crewai import Agent, Crew, Process, Task  # noqa: E402

# ─── THE PEOPLE ──────────────────────────────────────────────────────────────
# role = job title · goal = what "done" means · backstory = how they behave.
# Keep each one to ONE job. That is the entire point of a team.

reviewer = Agent(
    role="Code Reviewer",
    goal="Find the most serious real problems in a piece of Python code",
    backstory=(
        "You review code for a living. You list problems clearly and you never "
        "fix them yourself - fixing is somebody else's job."
    ),
    llm=setup_env.crew_llm(),  # one model object per agent (keeps the cost meter honest)
    verbose=False,
    max_iter=2,
)

fixer = Agent(
    role="Code Fixer",
    goal="Fix exactly the problems you are handed, and nothing else",
    backstory=(
        "You change as little as possible. If a problem is not on the list you "
        "were given, you leave that code exactly as it was."
    ),
    llm=setup_env.crew_llm(),  # one model object per agent (keeps the cost meter honest)
    verbose=False,
    max_iter=2,
)

teacher = Agent(
    role="Teacher",
    goal="Explain a code fix to a junior developer in plain words",
    backstory="You have three short bullet points and no jargon.",
    llm=setup_env.crew_llm(),  # one model object per agent (keeps the cost meter honest)
    verbose=False,
    max_iter=2,
)

# ─── THE WORK, AND THE NOTES THAT PASS BETWEEN THEM ──────────────────────────

review_task = Task(
    description=(
        "Review this Python code:\n\n{code}\n\n"
        "List at most 3 problems, most serious first, one line each. Do not fix anything."
    ),
    expected_output="A numbered list of at most 3 problems, one line each.",
    agent=reviewer,
)

fix_task = Task(
    description=(
        "Here is the original code:\n\n{code}\n\n"
        "Fix ONLY the problems in the Code Reviewer's list. Return the complete fixed code."
    ),
    expected_output="The complete fixed Python code and nothing else.",
    agent=fixer,
    context=[review_task],  # ◀── the note: the Fixer reads the Reviewer's list
)

teach_task = Task(
    description="Explain to a junior developer what was wrong and why the fix works.",
    expected_output="Exactly 3 short bullet points.",
    agent=teacher,
    context=[review_task, fix_task],  # ◀── two notes: the problems AND the fix
)

crew = Crew(
    agents=[reviewer, fixer, teacher],
    tasks=[review_task, fix_task, teach_task],
    process=Process.sequential,  # an assembly line: one after another, in this order
    verbose=False,
    tracing=False,
)

# ─── RUN IT AND WATCH THE NOTES MOVE ─────────────────────────────────────────


def main() -> int:
    sample_name, code = pick_sample(sys.argv)
    meter = Meter()

    print(banner(f"THE TEAM  ·  reviewing '{sample_name}'"))
    print(indent(code))
    print("\n⏳ The team is working (about 10 seconds)...")

    result = crew.kickoff(inputs={"code": code})
    meter.record_crew(result)

    review_note, fixed_code, lesson = (t.raw for t in result.tasks_output)

    print("\n📝 Reviewer ──▶ Fixer")
    print(indent(review_note))
    print("\n📝 Fixer ──▶ Teacher")
    print(indent(fixed_code))
    print("\n🎓 Teacher ──▶ you")
    print(indent(lesson))

    print("\n" + check_planted(sample_name, review_note))
    print("\n" + meter.card(agents=3, model=setup_env.MODEL))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
