"""
Live homework · Part A -- THE TEAM  (on your own)
The Dinner Party Desk passes NOTES.

    Planner ──note──▶ Chef ──note──▶ Host
    finds problems    fixes exactly   writes the invitation
    never cooks       those           to the guests

The same move as Exercise 1, on a new problem. Two TODOs, one line each.

This file RUNS right now. Run it first and read what the Chef and the Host
wrote. Then do TODO 1, run it again; then TODO 2, run it again.

Run:
    python hw_a_the_team.py            # the dinner party (3 planted problems)
    python hw_a_the_team.py picnic     # the picnic (1 planted problem)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "shared"))

import setup_env  # noqa: E402  ALWAYS FIRST
from meter import Meter, banner, indent  # noqa: E402
from menus import check_new_menu, check_planted, menu_of, pick_request  # noqa: E402

from crewai import Agent, Crew, Process, Task  # noqa: E402

# ─── THE PEOPLE (done for you) ──────────────────────────────────────────────
planner = Agent(
    role="Party Planner",
    goal="Find every problem between a menu and the guests who will eat it",
    backstory="You check menus against allergies, diets and the budget. You list the "
              "problems; you never change the menu yourself.",
    llm=setup_env.crew_llm(),
    verbose=False,
    max_iter=2,
)
chef = Agent(
    role="Chef",
    goal="Change a menu to fix exactly the problems you are handed, and nothing else",
    backstory="You keep every dish that has no problem. You change as little as possible.",
    llm=setup_env.crew_llm(),
    verbose=False,
    max_iter=2,
)
host = Agent(
    role="Host",
    goal="Write a short, warm invitation that tells the guests what they will eat",
    backstory="You are friendly and precise: you only mention dishes that are really on the menu.",
    llm=setup_env.crew_llm(),
    verbose=False,
    max_iter=2,
)

# ─── THE WORK ────────────────────────────────────────────────────────────────
check_task = Task(
    description=(
        "Here is a dinner request:\n\n{request}\n\n"
        "List every problem between the menu and the guests or the budget, most serious "
        "first, one line each. Do not change the menu."
    ),
    expected_output="A numbered list of problems, one line each.",
    agent=planner,
)

# ===== TODO 1 -- hand the Chef the Planner's note ================================
# The Chef sees ONLY the menu: not the guest list, not the budget. So how would it
# know that Sara has a peanut allergy? Run the file and look at the Chef's menu.
# Then give fix_task the note it needs.
fix_task = Task(
    description=(
        "Here is the current menu:\n\n{menu}\n\n"
        "Rewrite it so that it fixes exactly the problems in the Party Planner's list. "
        "Keep every dish that has no problem. End with the new estimated cost in dollars."
    ),
    expected_output="The complete new menu, one dish per line, then the estimated cost.",
    agent=chef,
    context=[check_task],
)

# ===== TODO 2 -- let the Host read the notes =====================================
# The Host is handed nothing at all. Read its invitation: is that food on YOUR menu?
# Give it the two notes it needs: the problems (so it can reassure the guests)
# and the new menu.
invite_task = Task(
    description=(
        "Write the invitation for the guests in 4 short sentences. Say what will be served, "
        "and reassure anyone with an allergy or a special diet."
    ),
    expected_output="A 4-sentence invitation.",
    agent=host,
    context=[check_task, fix_task],
)

crew = Crew(
    agents=[planner, chef, host],
    tasks=[check_task, fix_task, invite_task],
    process=Process.sequential,
    verbose=False,
    tracing=False,
)


# ─── RUN IT AND WATCH THE NOTES MOVE ─────────────────────────────────────────
def main() -> int:
    name, request = pick_request(sys.argv)
    meter = Meter()

    print(banner(f"THE DINNER PARTY DESK  ·  the team  ·  '{name}'"))
    print(indent(request))
    print("\n⏳ The team is working (about 10 seconds)...")

    result = crew.kickoff(inputs={"request": request, "menu": menu_of(request)})
    meter.record_crew(result)
    problems, new_menu, invitation = (t.raw for t in result.tasks_output)

    print("\n📝 Planner ──▶ Chef")
    print(indent(problems))
    print("\n📝 Chef ──▶ Host")
    print(indent(new_menu))
    if not fix_task.context:
        print("\n   👀 Did the Chef fix anything that matters? It never saw the guest list,")
        print("      and nobody handed it the Planner's note (context=[]). That is TODO 1.")

    print("\n💌 Host ──▶ guests")
    print(indent(invitation))
    if not invite_task.context:
        print("\n   👀 Is that the food on YOUR menu? The Host was handed no notes (context=[]).")
        print("      That is TODO 2.")

    print("\n" + check_planted(name, problems))
    print(check_new_menu(request, new_menu))
    print("\n" + meter.card(agents=3, model=setup_env.MODEL))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
