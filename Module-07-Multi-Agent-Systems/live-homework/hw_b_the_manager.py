"""
Live homework · Part B -- THE MANAGER  (on your own)
The Dinner Party Desk shares a WHITEBOARD.

   request ──▶ HEAD PLANNER ──▶ [allergy] [diet] [budget] [variety] ──▶ HEAD PLANNER ──▶ verdict
               decides who works    only the chosen ones, all AT ONCE      reads the board

The same moves as Exercise 2, on a new problem. Two TODOs.

  TODO 1  ROUTING   the model REQUESTS a team -- your code DECIDES
  TODO 2  PARALLEL  send the work to the whole team -- and give the whiteboard its
                    merge rule, or you will meet the crash from Exercise 2 again

This file RUNS right now. Run it first, then after each TODO.

Run:
    python hw_b_the_manager.py            # the dinner party: a big team should be picked
    python hw_b_the_manager.py picnic     # the picnic: a small team should be picked
"""

import operator
import re
import sys
import time
from pathlib import Path
from typing import Annotated, TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "shared"))

import setup_env  # noqa: E402  ALWAYS FIRST
from meter import Meter, banner, indent  # noqa: E402
from menus import check_planted, pick_request  # noqa: E402

from langgraph.errors import InvalidUpdateError  # noqa: E402
from langgraph.graph import END, START, StateGraph  # noqa: E402

# ─── THE SPECIALISTS (done for you) ──────────────────────────────────────────
SPECIALISTS = {
    "allergy": "Check ONLY food allergies: any dish that contains what a guest is allergic to.",
    "diet": "Check ONLY dietary needs: every vegetarian or vegan guest must have a main dish they can eat.",
    "budget": "Check ONLY the estimated cost against the budget.",
    "variety": "Check ONLY variety and balance: too much of one thing, nothing fresh, no dessert.",
}
STAY_IN_LANE = "If a problem belongs to another specialist's area, leave it out: they will report it."
MAX_SPECIALISTS = 3  # the budget: never more than 3 specialists on one request


# ─── THE WHITEBOARD ──────────────────────────────────────────────────────────
class Whiteboard(TypedDict):
    request: str
    asked: str
    team: list[str]
    findings: Annotated[list[str], operator.add]
    timings: Annotated[list[float], operator.add]
    fanout_started: float
    parallel_seconds: float
    verdict: str
    summary: str


llm = setup_env.graph_llm()
meter = Meter()


def ask(instructions: str, message: str) -> str:
    reply = llm.invoke([("system", instructions), ("user", message)])
    meter.record(reply)
    return reply.content.strip()


# ─── 1 · ROUTING ─────────────────────────────────────────────────────────────
def lead_decides(board: Whiteboard) -> dict:
    reply = ask(
        "You are the head party planner and you staff a checking team. Do NOT check the menu "
        "yourself. Choose which specialists this request needs. Each one costs time and money, "
        "so choose ONLY the relevant ones:\n"
        + "\n".join(f"- {name}: {job}" for name, job in SPECIALISTS.items())
        + "\nReply with the chosen names only, comma-separated. Example: allergy, budget",
        board["request"],
    )
    words = re.split(r"[^a-z]+", reply.lower())
    team = [name for name in dict.fromkeys(words) if name in SPECIALISTS][:MAX_SPECIALISTS]
    if not team:
        team = ["budget"]
    print(f"🧭 Head planner chose: {', '.join(team)}     (the model said: {reply!r})")
    return {"asked": reply, "team": team, "fanout_started": time.perf_counter()}


# ─── 2 · PARALLEL ────────────────────────────────────────────────────────────
def send_to_team(board: Whiteboard) -> list[str]:
    return board["team"]


def make_specialist(name: str, job: str):
    def specialist(board: Whiteboard) -> dict:
        started = time.perf_counter()
        reply = ask(
            f"You are the {name} specialist for a dinner party. {job} {STAY_IN_LANE} "
            "List at most 3 problems, one per line. Start each line with "
            "BLOCKER: (the menu must change) or MINOR: (nice to fix). "
            "If you find nothing in your area, reply exactly: NONE",
            board["request"],
        )
        took = time.perf_counter() - started
        lines = [ln.strip() for ln in reply.splitlines()
                 if ln.strip().upper().startswith(("BLOCKER", "MINOR"))]
        print(f"   ✍️  {name:<8} wrote {len(lines)} line(s) on the whiteboard  ({took:.1f} s)")
        return {"findings": [f"[{name}] {ln}" for ln in lines], "timings": [took]}

    specialist.__name__ = name
    return specialist


# ─── the head planner reads the whole whiteboard ─────────────────────────────
def lead_summarizes(board: Whiteboard) -> dict:
    parallel_seconds = time.perf_counter() - board["fanout_started"]
    # The verdict is decided by CODE: any BLOCKER means the menu must change.
    blocked = any(re.search(r"\]\s*BLOCKER", f, re.IGNORECASE) for f in board["findings"])
    summary = ask(
        "You are the head party planner. Summarise your team's findings for the host "
        "in exactly 3 short bullets, most important first.",
        "\n".join(board["findings"]) or "The team found no problems.",
    )
    return {"verdict": "CHANGE THE MENU" if blocked else "GOOD TO GO",
            "summary": summary, "parallel_seconds": parallel_seconds}


def build_graph():
    graph = StateGraph(Whiteboard)
    graph.add_node("lead_decides", lead_decides)
    for name, job in SPECIALISTS.items():
        graph.add_node(name, make_specialist(name, job))
        graph.add_edge(name, "lead_summarizes")
    graph.add_node("lead_summarizes", lead_summarizes)
    graph.add_edge(START, "lead_decides")
    graph.add_conditional_edges("lead_decides", send_to_team, list(SPECIALISTS))
    graph.add_edge("lead_summarizes", END)
    return graph.compile()


def main() -> int:
    name, request = pick_request(sys.argv)
    print(banner(f"THE DINNER PARTY DESK  ·  the manager  ·  '{name}'"))
    print(indent(request))
    print()

    try:
        board = build_graph().invoke({"request": request, "findings": [], "timings": []},
                                     config={"recursion_limit": 10})
    except InvalidUpdateError as crash:
        print("\n💥 CRASH -- you have met this one before, in Exercise 2.")
        print(indent(str(crash).splitlines()[0]))
        print("\n   Several specialists wrote `findings` at the same moment. TODO 2 has a")
        print("   second half: give `findings` its merge rule in the Whiteboard class.")
        return 1

    print("\n📋 THE WHITEBOARD")
    print(indent("\n".join(board["findings"]) or "(nothing)"))
    print(f"\n🏁 VERDICT: {board['verdict']}   (decided by code: any BLOCKER means the menu must change)")
    print(indent(board["summary"]))

    worked = len(board["timings"])
    if worked < len(board["team"]):
        print(f"\n👀 The head planner chose {len(board['team'])} specialist(s) but only {worked} worked. That is TODO 2.")
    if board["team"] == ["budget"] and "allergy" in board["asked"].lower():
        print("\n👀 The model asked for the allergy specialist, and your code ignored it. That is TODO 1.")
    print(f"\n⏱  {worked} specialist(s) worked in parallel: {board['parallel_seconds']:.1f} s"
          f"   (one after another: {sum(board['timings']):.1f} s)")
    print("\n" + check_planted(name, "\n".join(board["findings"])))
    print("\n" + meter.card(agents=worked + 1, model=setup_env.MODEL))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
