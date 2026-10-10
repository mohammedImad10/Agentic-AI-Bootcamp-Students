"""
Exercise 1 -- THE TEAM  (STARTER)
Agents share information by PASSING A NOTE.

    Reviewer ──note──▶ Fixer ──note──▶ Teacher

Three agents. One job each. Each one sees only the notes it is handed.

    Reviewer   finds the problems        (never fixes anything)       ✅ done for you
    Fixer      fixes exactly those       (sees the code + the note)   ✋ TODO 1, TODO 2
    Teacher    explains it to a junior   (sees the notes)             ✋ TODO 3

This file RUNS right now, before you change anything. Run it first, read what
it prints, then do the TODOs in order and run it again after each one.

In CrewAI the note is `context=[...]`: the list of earlier tasks whose output
this task is allowed to read.

Run:
    python team_starter.py
    python team_starter.py split_bill     # a different piece of code
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

# ===== TODO 1 -- hire the Fixer ===============================================
# Copy the Reviewer above and change three things:
#   role      = "Code Fixer"
#   goal      = fix exactly the problems it is handed, and nothing else
#   backstory = it changes as little as possible
fixer = None

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

# ===== TODO 2 -- give the Fixer its work, and hand it the Reviewer's note =====
# A Task needs: description, expected_output, agent, and context.
#   description      the original code is available as {code}. Tell it to fix ONLY
#                    the problems on the Code Reviewer's list.
#   expected_output  "The complete fixed Python code and nothing else."
#   agent            fixer
#   context          [review_task]      <-- THIS is the note being passed
fix_task = None

# ===== TODO 3 -- let the Teacher read the notes ================================
# Right now the Teacher is handed NOTHING: context=[] means "read no notes".
# Run the file and read the Teacher's bullets. Are they about THIS code?
# Then hand it the two notes it needs: the problems, and the fix.
teach_task = Task(
    description="Explain to a junior developer what was wrong and why the fix works.",
    expected_output="Exactly 3 short bullet points.",
    agent=teacher,
    context=[],  # TODO 3: which notes should the Teacher read?
)

# ─── THE CREW (builds itself from whatever you have finished) ─────────────────

agents = [a for a in (reviewer, fixer, teacher) if a is not None]
tasks = [t for t in (review_task, fix_task, teach_task) if t is not None]

crew = Crew(
    agents=agents,
    tasks=tasks,
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
    print(f"\n⏳ {len(agents)} agent(s) working...")

    result = crew.kickoff(inputs={"code": code})
    meter.record_crew(result)

    print("\n📝 Reviewer ──▶ Fixer")
    print(indent(review_task.output.raw))

    print("\n📝 Fixer ──▶ Teacher")
    if fix_task is None:
        print("   ✋ Nobody is fixing anything yet. Do TODO 1 and TODO 2.")
    else:
        print(indent(fix_task.output.raw))

    print("\n🎓 Teacher ──▶ you")
    print(indent(teach_task.output.raw))
    if not teach_task.context:
        print("\n   👀 Is that explanation about THIS code, or just about code in general?")
        print("      The Teacher was handed no notes (context=[]). That is TODO 3.")

    print("\n" + check_planted(sample_name, review_task.output.raw))
    print("\n" + meter.card(agents=len(agents), model=setup_env.MODEL))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
