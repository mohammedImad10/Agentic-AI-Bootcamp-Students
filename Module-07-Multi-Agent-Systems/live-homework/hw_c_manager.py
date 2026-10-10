"""
Live homework · Part C -- THE PHONE CALL  ·  the MANAGER  (client, on your own)

Your party manager checks diet, budget and variety itself. Allergies belong to
the clinic: their Allergy Desk runs in another program (CrewAI) and you can only
CALL it, over A2A. The phone -- card, message, task -- is done for you: you
built it together in Exercise 3.

    your LangGraph manager  ──── A2A ────▶  the clinic's Allergy Desk
    (this file, TERMINAL 2)                 (hw_c_allergy_desk.py, TERMINAL 1)

A guest's allergy is medical information: only the clinic's desk receives it.
Your local specialists see the menu, the budget and the diets -- nothing more.

Two TODOs:
    TODO 1  the Allergy Desk's CARD         (in hw_c_allergy_desk.py)
    TODO 2  FAIL CLOSED when it can't answer (in this file)

Run (TERMINAL 2, while the desk runs in TERMINAL 1):
    python hw_c_manager.py            # 'sara': ONE problem, and it is the allergy
    python hw_c_manager.py party      # the full dinner party
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
from menus import check_planted, pick_request  # noqa: E402

from langgraph.graph import END, START, StateGraph  # noqa: E402

DEFAULT_DESK = "http://127.0.0.1:9998"
CARD_PATH = "/.well-known/agent-card.json"

LOCAL_SPECIALISTS = {
    "diet": "Check ONLY dietary needs: every vegetarian or vegan guest must have a main dish they can eat.",
    "budget": "Check ONLY the estimated cost against the budget.",
    "variety": "Check ONLY variety and balance: too much of one thing, nothing fresh, no dessert.",
}
REMOTE_ALLERGY = "Check ONLY food allergies (the clinic's Allergy Desk, another program)."
STAY_IN_LANE = ("If a problem belongs to another specialist's area, leave it out: they will report it. "
                "Allergies are the Allergy Desk's job: never mention them.")
MENU = {**LOCAL_SPECIALISTS, "allergy": REMOTE_ALLERGY}
MAX_SPECIALISTS = 3


# ═══ A2A: THE PHONE (done for you -- Exercise 3) ═════════════════════════════
def read_card(desk: str) -> dict:
    with urllib.request.urlopen(desk.rstrip("/") + CARD_PATH, timeout=10) as reply:
        return json.load(reply)


def offers(card: dict, tag: str) -> bool:
    return any(tag in skill.get("tags", []) for skill in card.get("skills", []))


def phone(card: dict, text: str) -> str:
    call = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "SendMessage",
        "params": {"message": {"role": "ROLE_USER", "messageId": str(uuid.uuid4()),
                               "parts": [{"text": text}]}},
    }
    request = urllib.request.Request(
        card["supportedInterfaces"][0]["url"],
        data=json.dumps(call).encode("utf-8"),
        headers={"Content-Type": "application/json", "A2A-Version": "1.0"},
    )
    with urllib.request.urlopen(request, timeout=120) as reply:
        answer = json.load(reply)
    if "error" in answer:
        raise RuntimeError(f"the desk refused the call: {answer['error']['message']}")
    task = (answer.get("result") or {}).get("task") or {}
    if (task.get("status") or {}).get("state") != "TASK_STATE_COMPLETED":
        raise RuntimeError("the desk did not finish the task")
    return "\n".join(part["text"] for artifact in task.get("artifacts", [])
                     for part in artifact.get("parts", []) if "text" in part)


# ─── THE WHITEBOARD ──────────────────────────────────────────────────────────
class Whiteboard(TypedDict):
    request: str
    team: list[str]
    findings: Annotated[list[str], operator.add]
    timings: Annotated[list[float], operator.add]
    fanout_started: float
    verdict: str
    summary: str


llm = setup_env.graph_llm()
meter = Meter()
desk_card: dict | None = None
why_no_desk = "we have not read its card yet"
allergy_missing: list[str] = []  # filled in when the allergy check could not happen


def ask(instructions: str, message: str) -> str:
    reply = llm.invoke([("system", instructions), ("user", message)])
    meter.record(reply)
    return reply.content.strip()


def only_findings(text: str) -> list[str]:
    return [ln.strip() for ln in text.splitlines() if ln.strip().upper().startswith(("BLOCKER", "MINOR"))]


def without_medical_details(request: str) -> str:
    """What the LOCAL specialists see: the menu, the budget and the diets -- no allergies.

    A guest's allergy is medical information. It goes to the clinic's Allergy Desk and
    to nobody else (need to know: each agent gets only what its job needs).
    """
    return re.sub(r"[^.\n]*\ballerg\w*[^.\n]*\.\s*", "", request)


def lead_decides(board: Whiteboard) -> dict:
    reply = ask(
        "You are the head party planner and you staff a checking team. Do NOT check the menu "
        "yourself. Choose which specialists this request needs. Each one costs time and money, "
        "so choose ONLY the relevant ones:\n"
        + "\n".join(f"- {name}: {job}" for name, job in MENU.items())
        + "\nReply with the chosen names only, comma-separated. Example: allergy, budget",
        board["request"],
    )
    words = re.split(r"[^a-z]+", reply.lower())
    team = [w for w in dict.fromkeys(words) if w in MENU][:MAX_SPECIALISTS] or ["allergy"]
    where = {n: ("📞 A2A" if n == "allergy" else "local") for n in team}
    print(f"🧭 Head planner chose: {', '.join(f'{n} ({where[n]})' for n in team)}")
    return {"team": team, "fanout_started": time.perf_counter()}


def send_to_team(board: Whiteboard) -> list[str]:
    return board["team"]


def make_local_specialist(name: str, job: str):
    def specialist(board: Whiteboard) -> dict:
        started = time.perf_counter()
        lines = only_findings(ask(
            f"You are the {name} specialist for a dinner party. {job} {STAY_IN_LANE} "
            "List at most 3 problems, one per line. Start each line with "
            "BLOCKER: (the menu must change) or MINOR: (nice to fix). "
            "If you find nothing in your area, reply exactly: NONE",
            without_medical_details(board["request"]),
        ))
        took = time.perf_counter() - started
        print(f"   ✍️  {name:<8} wrote {len(lines)} line(s)             ({took:.1f} s, local)")
        return {"findings": [f"[{name}] {ln}" for ln in lines], "timings": [took]}

    specialist.__name__ = name
    return specialist


def allergy_desk(board: Whiteboard) -> dict:
    """The allergy 'specialist' is a phone call to the clinic's agent."""
    started = time.perf_counter()
    try:
        if desk_card is None:
            raise ConnectionError(why_no_desk)
        lines = only_findings(phone(desk_card, board["request"]))
        took = time.perf_counter() - started
        print(f"   📞 allergy    answered with {len(lines)} line(s)      ({took:.1f} s, over A2A)")
    except Exception as problem:  # noqa: BLE001
        took = time.perf_counter() - started
        allergy_missing.append(str(problem))
        print(f"   ☎️  allergy    no answer ({problem})")
        lines = [f"BLOCKER: Allergy check could not be completed: {problem}"]
    return {"findings": [f"[allergy·A2A] {ln}" for ln in lines], "timings": [took]}


def lead_summarizes(board: Whiteboard) -> dict:
    blocked = any(re.search(r"\]\s*BLOCKER", f, re.IGNORECASE) for f in board["findings"])
    summary = ask(
        "You are the head party planner. Summarise your team's findings for the host "
        "in exactly 3 short bullets, most important first.",
        "\n".join(board["findings"]) or "The team found no problems.",
    )
    return {"verdict": "CHANGE THE MENU" if blocked else "GOOD TO GO", "summary": summary}


def build_graph():
    graph = StateGraph(Whiteboard)
    graph.add_node("lead_decides", lead_decides)
    for name, job in LOCAL_SPECIALISTS.items():
        graph.add_node(name, make_local_specialist(name, job))
        graph.add_edge(name, "lead_summarizes")
    graph.add_node("allergy", allergy_desk)
    graph.add_edge("allergy", "lead_summarizes")
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
    name, request = pick_request(argv, default="sara")

    print(banner(f"THE DINNER PARTY DESK  ·  the phone call  ·  '{name}'"))
    print(indent(request))

    # ── discovery: read the card before trusting anyone with our guests' health
    try:
        card = read_card(desk)
        print(f"\n📇 {card['name']}: {card['description'] or '(no description)'}")
        if offers(card, "allergy"):
            desk_card = card
            print(f"   ✅ it offers an 'allergy' skill; calls go to {card['supportedInterfaces'][0]['url']}")
        else:
            why_no_desk = "its card does not offer an 'allergy' skill"
            print("   ⛔ the card does not advertise an 'allergy' skill, so we will not call it (TODO 1)")
    except (urllib.error.URLError, OSError) as problem:
        why_no_desk = f"nobody answered at {desk}"
        print(f"\n☎️  No answer at {desk}: {problem}")
        print("   Is the Allergy Desk running in TERMINAL 1?   python hw_c_allergy_desk.py")

    print()
    board = build_graph().invoke({"request": request, "findings": [], "timings": []},
                                 config={"recursion_limit": 10})

    print("\n📋 THE WHITEBOARD  (local specialists + the phone call)")
    print(indent("\n".join(board["findings"]) or "(nothing)"))
    print(f"\n🏁 VERDICT: {board['verdict']}   (decided by code: any BLOCKER means the menu must change)")
    print(indent(board["summary"]))

    silent = allergy_missing and not any(f.startswith("[allergy") for f in board["findings"])
    if silent and board["verdict"] == "GOOD TO GO":
        print("\n👀 The allergy check NEVER happened -- and your manager says GOOD TO GO.")
        print("   Would you serve this dinner to Sara? That is TODO 2: fail closed.")
    elif silent:
        print("\n👀 The allergy check never happened, and nothing on the whiteboard says so.")
        print("   The other specialists saved you this time. Would they always? That is TODO 2.")

    print("\n" + check_planted(name, "\n".join(board["findings"])))
    print("\n" + meter.card(agents=len(board["team"]) + 1, model=setup_env.MODEL,
                            note="the Allergy Desk's tokens are not in here: it spent them in ITS program"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
