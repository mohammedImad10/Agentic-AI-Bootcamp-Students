"""
Exercise 2 -- THE MANAGER  (STARTER)
Agents share information on a WHITEBOARD (shared state).

                  ┌──────────────────── the whiteboard ─────────────────────┐
  code ──▶ LEAD ──▶ [correctness] [security] [performance] [readability]    ──▶ LEAD ──▶ verdict
         decides  │  only the ones the lead chose, all working AT THE SAME TIME  │   reads the board
         who works└──────────────────────────────────────────────────────────┘

Three TODOs, one idea each. This file RUNS right now. Run it after every TODO:

  TODO 1  ROUTING       the lead decides who works -- and code CHECKS that decision
  TODO 2  PARALLEL      send the work to everyone the lead chose, at the same time
  TODO 3  SHARED STATE  give the whiteboard a rule for combining writes
                        (TODO 2 will crash on purpose. TODO 3 is the fix.)

Run:
    python manager_starter.py              # 'orders' touches a database
    python manager_starter.py split_bill   # pure arithmetic: a different team should be picked
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
from samples import check_planted, pick_sample  # noqa: E402

from langgraph.errors import InvalidUpdateError  # noqa: E402
from langgraph.graph import END, START, StateGraph  # noqa: E402

# ─── THE SPECIALISTS ─────────────────────────────────────────────────────────
# Each one gets its OWN short instructions and nothing else. Small, clean context.
SPECIALISTS = {
    "correctness": "Check ONLY correctness: crashes, wrong results (including amounts that do not add up), "
                   "unhandled edge cases such as empty input or zero, and resources left open "
                   "(files, database connections).",
    "security": "Check ONLY security: injection, secrets in code, unsafe handling of user input.",
    "performance": "Check ONLY performance: wasted work, slow loops, work the database could do instead.",
    "readability": "Check ONLY readability: naming, structure, missing docstring.",
}
STAY_IN_LANE = "If a problem belongs to another specialist's area, leave it out: they will report it."

MAX_SPECIALISTS = 3  # the budget: never pay for more than 3 specialists on one review


# ─── THE WHITEBOARD (shared state) ───────────────────────────────────────────
class Whiteboard(TypedDict):
    code: str
    team: list[str]
    # ===== TODO 3 -- a rule for combining writes ==============================
    # Several specialists write `findings` AT THE SAME MOMENT. Look at how
    # `timings` (two lines down) is declared, and declare `findings` the same way.
    # operator.add means: "add the new lines to the list, don't replace it".
    findings: list[str]
    timings: Annotated[list[float], operator.add]  # <- done for you: copy this pattern
    fanout_started: float
    parallel_seconds: float
    verdict: str
    summary: str


llm = setup_env.graph_llm()
meter = Meter()


def ask(instructions: str, message: str) -> str:
    """One LLM call: instructions + a message in, text out. Counted by the meter."""
    reply = llm.invoke([("system", instructions), ("user", message)])
    meter.record(reply)
    return reply.content.strip()


# ─── 1 · ROUTING: the lead decides who works ─────────────────────────────────
def lead_decides(board: Whiteboard) -> dict:
    reply = ask(
        "You are the lead code reviewer. Decide which specialists this code needs. "
        "Each specialist costs time and money, so pick ONLY the relevant ones.\n"
        + "\n".join(f"- {name}: {job}" for name, job in SPECIALISTS.items())
        + "\nReply with their names only, comma-separated.",
        board["code"],
    )
    # ===== TODO 1 -- the model REQUESTS a team, code DECIDES =================
    # `reply` is whatever the model typed, e.g. "correctness, security, performance, readability".
    # Turn it into `team`, a list that is guaranteed to be safe:
    #   a. split the reply into words:        re.split(r"[^a-z]+", reply.lower())
    #   b. keep only real specialist names:   w in SPECIALISTS   (drop duplicates too)
    #   c. never more than the budget:        [:MAX_SPECIALISTS]
    #   d. never nobody:                      team or ["correctness"]
    team = ["correctness"]  # <- replace this line
    print(f"🧭 Lead chose: {', '.join(team)}     (the model said: {reply!r})")
    return {"team": team, "fanout_started": time.perf_counter()}


# ─── 2 · PARALLEL: send the work to everyone chosen, at once ─────────────────
def send_to_team(board: Whiteboard) -> list[str]:
    # ===== TODO 2 -- fan out ==================================================
    # Return the lead's list (board["team"]) instead of just ["correctness"].
    # Returning a LIST makes LangGraph run every node in it AT THE SAME TIME.
    return ["correctness"]  # <- replace this line


def make_specialist(name: str, job: str):
    def specialist(board: Whiteboard) -> dict:
        started = time.perf_counter()
        reply = ask(
            f"You are the {name} specialist. {job} {STAY_IN_LANE} "
            "List at most 3 problems, one per line. Start each line with "
            "BLOCKER: (must fix before merging) or MINOR: (nice to fix). "
            "If you find nothing in your area, reply exactly: NONE",
            board["code"],
        )
        took = time.perf_counter() - started
        lines = [ln.strip() for ln in reply.splitlines()
                 if ln.strip().upper().startswith(("BLOCKER", "MINOR"))]
        print(f"   ✍️  {name:<12} wrote {len(lines)} line(s) on the whiteboard  ({took:.1f} s)")
        return {"findings": [f"[{name}] {ln}" for ln in lines], "timings": [took]}

    specialist.__name__ = name
    return specialist


# ─── the lead reads the whole whiteboard ─────────────────────────────────────
def lead_summarizes(board: Whiteboard) -> dict:
    parallel_seconds = time.perf_counter() - board["fanout_started"]
    # The verdict is decided by CODE, not by a model: any BLOCKER blocks the merge.
    blocked = any(re.search(r"\]\s*BLOCKER", f, re.IGNORECASE) for f in board["findings"])
    summary = ask(
        "You are the lead code reviewer. Summarise your team's findings for the author "
        "in exactly 3 short bullets, most important first.",
        "\n".join(board["findings"]) or "The team found no problems.",
    )
    return {
        "verdict": "BLOCK" if blocked else "APPROVE",
        "summary": summary,
        "parallel_seconds": parallel_seconds,
    }


# ─── wire it up (already done for you) ───────────────────────────────────────
def build_graph():
    graph = StateGraph(Whiteboard)
    graph.add_node("lead_decides", lead_decides)
    for name, job in SPECIALISTS.items():
        graph.add_node(name, make_specialist(name, job))
        graph.add_edge(name, "lead_summarizes")  # fan-in: everyone reports back
    graph.add_node("lead_summarizes", lead_summarizes)

    graph.add_edge(START, "lead_decides")
    graph.add_conditional_edges("lead_decides", send_to_team, list(SPECIALISTS))  # fan-out
    graph.add_edge("lead_summarizes", END)
    return graph.compile()


def main() -> int:
    app = build_graph()
    sample_name, code = pick_sample(sys.argv)
    print(banner(f"THE MANAGER  ·  reviewing '{sample_name}'"))
    print(indent(code))
    print()

    try:
        board = app.invoke(
            {"code": code, "findings": [], "timings": []},
            config={"recursion_limit": 10},  # a hard stop: at most 10 steps, whatever happens
        )
    except InvalidUpdateError as crash:
        print("\n💥 CRASH -- and this one is on purpose.")
        print(indent(str(crash).splitlines()[0]))
        print("\n   Several specialists wrote on the whiteboard at the SAME moment, and the")
        print("   whiteboard has no rule for combining their writes, so LangGraph refused")
        print("   rather than silently keep one and throw the others away.")
        print("   That is TODO 3.")
        return 1

    print("\n📋 THE WHITEBOARD  (what the team wrote)")
    print(indent("\n".join(board["findings"]) or "(nothing)"))
    print(f"\n🏁 VERDICT: {board['verdict']}   (decided by code: any BLOCKER blocks the merge)")
    print(indent(board["summary"]))

    worked = len(board["timings"])
    if worked < len(board["team"]):
        print(f"\n👀 The lead chose {len(board['team'])} specialist(s) but only {worked} worked. That is TODO 2.")
    one_after_another = sum(board["timings"])
    print(f"\n⏱  {worked} specialist(s) worked in parallel: {board['parallel_seconds']:.1f} s"
          f"   (one after another: {one_after_another:.1f} s)")
    print("\n" + check_planted(sample_name, "\n".join(board["findings"])))
    print("\n" + meter.card(agents=worked + 1, model=setup_env.MODEL))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
