"""
Exercise 3 -- THE PHONE CALL  ·  the MANAGER calls another team  (client, SOLUTION)

This is the manager from Exercise 2 with one change: the security specialist
no longer lives in this file. It belongs to the Security Team, runs in its own
process, and is built with a different framework (CrewAI). We cannot import
it, read its prompt or share its memory. We can only CALL it.

    LangGraph manager  ──── A2A over HTTP ────▶  CrewAI Security Desk
    (this file)            read the card,        (security_desk_solution.py)
                           then SendMessage

How we find it: we are told where its business card is, and nothing else.
The card tells us what it can do (skills) and where to call (supportedInterfaces).

A2A has three nouns:
    the CARD     who the desk is and what it can do   (security_desk_solution.py)
    the MESSAGE  what we send                         (phone(), below)
    the TASK     what comes back, and how to read it  (phone(), below)

Run (TERMINAL 2, while the desk runs in TERMINAL 1):
    python manager_a2a_solution.py
    python manager_a2a_solution.py split_bill
    python manager_a2a_solution.py --desk http://192.168.1.23:9999   # a classmate's desk
"""

import json
import operator
import re
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Annotated, TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "shared"))

import setup_env  # noqa: E402  ALWAYS FIRST
from meter import Meter, banner, indent  # noqa: E402
from samples import check_planted, pick_sample  # noqa: E402

from langgraph.graph import END, START, StateGraph  # noqa: E402

DEFAULT_DESK = "http://127.0.0.1:9999"
CARD_PATH = "/.well-known/agent-card.json"

# ─── the specialists that still live HERE ────────────────────────────────────
LOCAL_SPECIALISTS = {
    "correctness": "Check ONLY correctness: crashes, wrong results (including amounts that do not add up), "
                   "unhandled edge cases such as empty input or zero, and resources left open "
                   "(files, database connections).",
    "performance": "Check ONLY performance: wasted work, slow loops, work the database could do instead.",
    "readability": "Check ONLY readability: naming, structure, missing docstring.",
}
REMOTE_SECURITY = "Check ONLY security: injection, secrets in code, unsafe handling of user input."
STAY_IN_LANE = "If a problem belongs to another specialist's area, leave it out: they will report it."
MENU = {**LOCAL_SPECIALISTS, "security": REMOTE_SECURITY}
MAX_SPECIALISTS = 3


# ═══ A2A: THE PHONE ══════════════════════════════════════════════════════════
def read_business_card(desk: str) -> dict:
    """Discovery: fetch the agent's card from its well-known address."""
    with urllib.request.urlopen(desk.rstrip("/") + CARD_PATH, timeout=10) as reply:
        return json.load(reply)


def offers(card: dict, tag: str) -> bool:
    """Does the card advertise a skill with this tag? We call agents for what they SAY they do."""
    return any(tag in skill.get("tags", []) for skill in card.get("skills", []))


def phone(card: dict, text: str) -> str:
    """Send one message to the agent described by `card` and return its answer."""
    call = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "SendMessage",
        "params": {
            "message": {
                "role": "ROLE_USER",
                "messageId": str(uuid.uuid4()),
                "parts": [{"text": text}],
            }
        },
    }
    url = card["supportedInterfaces"][0]["url"]  # the card tells us where to call
    request = urllib.request.Request(
        url,
        data=json.dumps(call).encode("utf-8"),
        headers={"Content-Type": "application/json", "A2A-Version": "1.0"},
    )
    with urllib.request.urlopen(request, timeout=120) as reply:
        answer = json.load(reply)

    if "error" in answer:
        raise RuntimeError(f"the desk refused the call: {answer['error']['message']}")
    task = (answer.get("result") or {}).get("task")
    if not task:
        raise RuntimeError("the reply has no Task in it: the desk is not answering in A2A shape")
    state = (task.get("status") or {}).get("state")
    if state != "TASK_STATE_COMPLETED":
        raise RuntimeError(f"the desk did not finish: {state}")
    return "\n".join(part["text"] for artifact in task.get("artifacts", [])
                     for part in artifact.get("parts", []) if "text" in part)


# ─── THE WHITEBOARD ──────────────────────────────────────────────────────────
class Whiteboard(TypedDict):
    code: str
    team: list[str]
    findings: Annotated[list[str], operator.add]
    timings: Annotated[list[float], operator.add]
    fanout_started: float
    parallel_seconds: float
    verdict: str
    summary: str


llm = setup_env.graph_llm()
meter = Meter()
desk_card: dict | None = None  # filled in by main() after reading the card
why_no_desk = "we have not read its business card yet"


def ask(instructions: str, message: str) -> str:
    reply = llm.invoke([("system", instructions), ("user", message)])
    meter.record(reply)
    return reply.content.strip()


def only_findings(text: str) -> list[str]:
    return [ln.strip() for ln in text.splitlines() if ln.strip().upper().startswith(("BLOCKER", "MINOR"))]


def lead_decides(board: Whiteboard) -> dict:
    reply = ask(
        "You are the lead code reviewer. Decide which specialists this code needs. "
        "Each specialist costs time and money, so pick ONLY the relevant ones.\n"
        + "\n".join(f"- {name}: {job}" for name, job in MENU.items())
        + "\nReply with their names only, comma-separated.",
        board["code"],
    )
    words = re.split(r"[^a-z]+", reply.lower())
    team = [w for w in dict.fromkeys(words) if w in MENU][:MAX_SPECIALISTS] or ["correctness"]
    where = {name: ("📞 A2A" if name == "security" else "local") for name in team}
    print(f"🧭 Lead chose: {', '.join(f'{n} ({where[n]})' for n in team)}")
    return {"team": team, "fanout_started": time.perf_counter()}


def send_to_team(board: Whiteboard) -> list[str]:
    return board["team"]


def make_local_specialist(name: str, job: str):
    def specialist(board: Whiteboard) -> dict:
        started = time.perf_counter()
        lines = only_findings(ask(
            f"You are the {name} specialist. {job} {STAY_IN_LANE} "
            "List at most 3 problems, one per line. Start each line with "
            "BLOCKER: (must fix before merging) or MINOR: (nice to fix). "
            "If you find nothing in your area, reply exactly: NONE",
            board["code"],
        ))
        took = time.perf_counter() - started
        print(f"   ✍️  {name:<12} wrote {len(lines)} line(s)             ({took:.1f} s, local)")
        return {"findings": [f"[{name}] {ln}" for ln in lines], "timings": [took]}

    specialist.__name__ = name
    return specialist


def security_desk(board: Whiteboard) -> dict:
    """The security 'specialist' is a phone call to another team's agent."""
    started = time.perf_counter()
    try:
        if desk_card is None:
            raise ConnectionError(why_no_desk)
        lines = only_findings(phone(desk_card, board["code"]))
        took = time.perf_counter() - started
        print(f"   📞 security     answered with {len(lines)} line(s)      ({took:.1f} s, over A2A)")
    except Exception as problem:  # noqa: BLE001
        # FAIL CLOSED: if the security check could not happen, we do NOT approve.
        took = time.perf_counter() - started
        print(f"   ☎️  security     no answer ({problem}) -> recorded as a BLOCKER")
        lines = [f"BLOCKER: the security review could not be done ({problem})."]
    return {"findings": [f"[security·A2A] {ln}" for ln in lines], "timings": [took]}


def lead_summarizes(board: Whiteboard) -> dict:
    parallel_seconds = time.perf_counter() - board["fanout_started"]
    blocked = any(re.search(r"\]\s*BLOCKER", f, re.IGNORECASE) for f in board["findings"])
    summary = ask(
        "You are the lead code reviewer. Summarise your team's findings for the author "
        "in exactly 3 short bullets, most important first.",
        "\n".join(board["findings"]) or "The team found no problems.",
    )
    return {"verdict": "BLOCK" if blocked else "APPROVE", "summary": summary,
            "parallel_seconds": parallel_seconds}


def build_graph():
    graph = StateGraph(Whiteboard)
    graph.add_node("lead_decides", lead_decides)
    for name, job in LOCAL_SPECIALISTS.items():
        graph.add_node(name, make_local_specialist(name, job))
        graph.add_edge(name, "lead_summarizes")
    graph.add_node("security", security_desk)
    graph.add_edge("security", "lead_summarizes")
    graph.add_node("lead_summarizes", lead_summarizes)
    graph.add_edge(START, "lead_decides")
    graph.add_conditional_edges("lead_decides", send_to_team, list(MENU))
    graph.add_edge("lead_summarizes", END)
    return graph.compile()


def main() -> int:
    global desk_card, why_no_desk
    desk = DEFAULT_DESK
    if "--desk" in sys.argv:
        desk = sys.argv[sys.argv.index("--desk") + 1]
    argv = [a for i, a in enumerate(sys.argv) if a != "--desk" and sys.argv[i - 1] != "--desk"]
    sample_name, code = pick_sample(argv)

    print(banner(f"THE PHONE CALL  ·  reviewing '{sample_name}'"))

    # ── discovery: read the business card BEFORE trusting anyone with our code
    try:
        card = read_business_card(desk)
        print(f"📇 Read the card at {desk}{CARD_PATH}")
        print(f"   {card['name']} (v{card['version']}): {card['description']}")
        for skill in card.get("skills", []):
            print(f"   skill: {skill['name']}  tags={skill.get('tags', [])}")
        if offers(card, "security"):
            desk_card = card
            print(f"   ✅ it offers a 'security' skill; calls go to {card['supportedInterfaces'][0]['url']}")
        else:
            why_no_desk = "its business card does not offer a 'security' skill"
            print("   ⛔ the card does not advertise a 'security' skill, so we will not send it our code")
    except (urllib.error.URLError, OSError) as problem:
        why_no_desk = f"nobody answered at {desk}"
        print(f"☎️  No answer at {desk}: {problem}")
        print("   Is the Security Desk running in TERMINAL 1?   python security_desk_solution.py")

    print()
    board = build_graph().invoke({"code": code, "findings": [], "timings": []},
                                 config={"recursion_limit": 10})

    print("\n📋 THE WHITEBOARD  (local specialists + the phone call)")
    print(indent("\n".join(board["findings"]) or "(nothing)"))
    print(f"\n🏁 VERDICT: {board['verdict']}   (decided by code: any BLOCKER blocks the merge)")
    print(indent(board["summary"]))
    print(f"\n⏱  {len(board['team'])} specialist(s) in parallel: {board['parallel_seconds']:.1f} s"
          f"   (one after another: {sum(board['timings']):.1f} s)")
    print("\n" + check_planted(sample_name, "\n".join(board["findings"])))
    print("\n" + meter.card(
        agents=len(board["team"]) + 1, model=setup_env.MODEL,
        note="the Security Desk's tokens are not in here: it spent them in ITS process",
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
