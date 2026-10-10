"""
Exercise 2 -- THE MANAGER  (SOLUTION)
Agents share information on a WHITEBOARD (shared state).

                  ┌──────────────────── the whiteboard ─────────────────────┐
  code ──▶ LEAD ──▶ [correctness] [security] [performance] [readability]    ──▶ LEAD ──▶ verdict
         decides  │  only the ones the lead chose, all working AT THE SAME TIME  │   reads the board
         who works└──────────────────────────────────────────────────────────┘

Three ideas in one file:

  1. ROUTING       the lead decides who works -- and code CHECKS that decision
  2. PARALLEL      the chosen specialists work at the same time (fan-out),
                   then the lead reads everything they wrote (fan-in)
  3. SHARED STATE  everyone writes on one whiteboard; when several write at the
                   same moment, the whiteboard needs a rule for combining them

In Exercise 1 the order was fixed: Reviewer, then Fixer, then Teacher, every
time. Here the lead decides at run time who is needed for THIS code.

Run:
    python manager_solution.py              # 'orders' touches a database
    python manager_solution.py split_bill   # pure arithmetic: watch the lead pick a smaller team
    python manager_solution.py --draw       # print the graph (paste it into https://mermaid.live)
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
    # Several specialists write here AT THE SAME MOMENT. `operator.add` is the
    # rule for combining their writes: add the new lines to the list.
    findings: Annotated[list[str], operator.add]
    timings: Annotated[list[float], operator.add]
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
    # The model REQUESTS a team. Code DECIDES what is allowed: only real names,
    # no duplicates, never more than the budget, and never nobody.
    words = re.split(r"[^a-z]+", reply.lower())
    team = [w for w in dict.fromkeys(words) if w in SPECIALISTS][:MAX_SPECIALISTS]
    team = team or ["correctness"]
    print(f"🧭 Lead chose: {', '.join(team)}     (the model said: {reply!r})")
    return {"team": team, "fanout_started": time.perf_counter()}


# ─── 2 · PARALLEL: send the work to everyone chosen, at once ─────────────────
def send_to_team(board: Whiteboard) -> list[str]:
    return board["team"]  # a LIST: LangGraph runs every node in it at the same time


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
        # 3 · SHARED STATE: this is added to the whiteboard, not overwriting it
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


# ─── wire it up ──────────────────────────────────────────────────────────────
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
    if "--draw" in sys.argv:
        print(app.get_graph().draw_mermaid())
        return 0

    sample_name, code = pick_sample(sys.argv)
    print(banner(f"THE MANAGER  ·  reviewing '{sample_name}'"))
    print(indent(code))
    print()

    board = app.invoke(
        {"code": code, "findings": [], "timings": []},
        config={"recursion_limit": 10},  # a hard stop: at most 10 steps, whatever happens
    )

    print("\n📋 THE WHITEBOARD  (what the team wrote)")
    print(indent("\n".join(board["findings"]) or "(nothing)"))
    print(f"\n🏁 VERDICT: {board['verdict']}   (decided by code: any BLOCKER blocks the merge)")
    print(indent(board["summary"]))

    one_after_another = sum(board["timings"])
    print(f"\n⏱  {len(board['team'])} specialist(s) worked in parallel: {board['parallel_seconds']:.1f} s"
          f"   (one after another: {one_after_another:.1f} s)")
    print("\n" + check_planted(sample_name, "\n".join(board["findings"])))
    print("\n" + meter.card(agents=len(board["team"]) + 1, model=setup_env.MODEL))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
