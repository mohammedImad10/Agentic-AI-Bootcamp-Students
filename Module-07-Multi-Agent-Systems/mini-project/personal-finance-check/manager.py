"""LangGraph budget manager with local specialists and an A2A FX desk."""

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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "shared"))

import setup_env  # noqa: E402  ALWAYS FIRST
from meter import Meter, banner, indent  # noqa: E402
from langgraph.graph import END, START, StateGraph  # noqa: E402

from finance_math import BASE_RATES_TO_USD, RATE_NOTE, calculate_budget, currencies_in  # noqa: E402
from manager_inputs import EXPECTED, INPUTS  # noqa: E402

DEFAULT_DESK = "http://127.0.0.1:9999"
CARD_PATH = "/.well-known/agent-card.json"

LOCAL_SPECIALISTS = {
    "spending": "Describe the largest spending categories and notable patterns. Do not calculate or announce the final budget decision.",
    "savings": "Assess the savings goal and identify a practical observation from the supplied monthly figures. Do not calculate or announce the final budget decision.",
}
REMOTE_FX = "Explain the currency conversion assumptions and FX uncertainty only. Never claim the supplied fixed rates are live."
STAY_IN_LANE = "If a problem belongs to another specialist's area, leave it out: that specialist will report it."
MENU = {**LOCAL_SPECIALISTS, "fx": REMOTE_FX}
MAX_SPECIALISTS = 2

class Whiteboard(TypedDict):
    data: dict
    team: list[str]
    findings: Annotated[list[str], operator.add]
    timings: Annotated[list[float], operator.add]
    failed_specialists: Annotated[list[str], operator.add]
    fx_ok: bool
    fanout_started: float
    parallel_seconds: float
    decision: str
    calculation: str
    summary: str


llm = setup_env.graph_llm()
meter = Meter()
desk_card: dict | None = None
why_no_desk = "we have not read its business card yet"


def ask(instructions: str, message: str) -> str:
    reply = llm.invoke([("system", instructions), ("user", message)])
    meter.record(reply)
    return reply.content.strip()


def read_business_card(desk: str) -> dict:
    with urllib.request.urlopen(desk.rstrip("/") + CARD_PATH, timeout=10) as reply:
        return json.load(reply)


def offers(card: dict, tag: str) -> bool:
    return any(tag in skill.get("tags", []) for skill in card.get("skills", []))


def phone(card: dict, text: str) -> str:
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
    request = urllib.request.Request(
        card["supportedInterfaces"][0]["url"],
        data=json.dumps(call).encode("utf-8"),
        headers={"Content-Type": "application/json", "A2A-Version": "1.0"},
    )
    with urllib.request.urlopen(request, timeout=120) as reply:
        answer = json.load(reply)
    if "error" in answer:
        raise RuntimeError(f"the FX desk refused the call: {answer['error']['message']}")
    task = (answer.get("result") or {}).get("task")
    if not task:
        raise RuntimeError("the reply has no Task in it")
    state = (task.get("status") or {}).get("state")
    if state != "TASK_STATE_COMPLETED":
        raise RuntimeError(f"the desk did not finish: {state}")
    return "\n".join(
        part["text"]
        for artifact in task.get("artifacts", [])
        for part in artifact.get("parts", [])
        if "text" in part
    )


def lead_decides(board: Whiteboard) -> dict:
    reply = ask(
        "You are a routing lead for a personal monthly budget. Do not review the budget, "
        "do not calculate totals, and do not give financial advice. Only choose the "
        "specialists needed. Reply with specialist names only, comma-separated; example: "
        "spending, savings. Available specialists:\n"
        + "\n".join(f"- {name}: {job}" for name, job in MENU.items()),
        json.dumps(board["data"], indent=2),
    )
    words = re.findall(r"[a-z]+", reply.lower())
    requested = list(dict.fromkeys(word for word in words if word in MENU))
    cross_currency = len(currencies_in(board["data"])) > 1

    # Validate the model's request against an allowed team, a 2-agent budget,
    # and the minimum coverage needed to make a defensible computation.
    required = ["fx", "spending"] if cross_currency else ["spending", "savings"]
    team = [name for name in requested if name in required]
    for name in required:
        if name not in team:
            team.append(name)
    team = team[:MAX_SPECIALISTS]
    print(f"🧭 Lead requested {requested or 'no valid specialists'}; validated team: {', '.join(team)}")
    return {"team": team, "fanout_started": time.perf_counter()}


def send_to_team(board: Whiteboard) -> list[str]:
    return board["team"]


def make_local_specialist(name: str, job: str):
    def specialist(board: Whiteboard) -> dict:
        started = time.perf_counter()
        currency_context = (
            "All amounts use the same currency; do not mention FX uncertainty."
            if len(currencies_in(board["data"])) == 1
            else "Mention foreign-currency exposure only; do not invent exchange rates."
        )
        reply = ask(
            f"You are the {name} specialist. {job} {currency_context} {STAY_IN_LANE} "
            f"Reply with exactly one line starting {name.upper()}: and no more than 35 words. "
            "Do not claim that missing information is a finding; reply exactly NONE if there is nothing useful.",
            json.dumps(board["data"], indent=2),
        )
        prefix = f"{name.upper()}:"
        line = next((line.strip() for line in reply.splitlines() if line.strip().upper().startswith(prefix)), "")
        took = time.perf_counter() - started
        print(f"   ✍️  {name:<10} wrote {1 if line else 0} line(s) ({took:.1f} s, local)")
        return {"findings": [f"[{name}] {line}" ] if line else [], "timings": [took]}

    specialist.__name__ = name
    return specialist


def fx_desk(board: Whiteboard) -> dict:
    started = time.perf_counter()
    try:
        if desk_card is None:
            raise ConnectionError(why_no_desk)
        message = {
            "budget": board["data"],
            "base_rates_to_usd": {code: str(rate) for code, rate in BASE_RATES_TO_USD.items()},
            "rate_note": RATE_NOTE,
        }
        answer = phone(desk_card, json.dumps(message, indent=2))
        line = next((line.strip() for line in answer.splitlines() if line.strip().upper().startswith("FX_NOTE:")), "")
        if not line:
            raise RuntimeError("the desk reply did not contain an FX_NOTE line")
        took = time.perf_counter() - started
        print(f"   📞 fx         answered with a note ({took:.1f} s, over A2A)")
        return {"findings": [f"[fx·A2A] {line}"], "timings": [took], "fx_ok": True}
    except Exception as problem:  # noqa: BLE001
        took = time.perf_counter() - started
        print(f"   ☎️  fx         no usable answer ({problem}) -> review required")
        return {
            "findings": [f"[fx·A2A] FX_ERROR: {problem}"],
            "timings": [took],
            "failed_specialists": ["fx"],
            "fx_ok": False,
        }


def lead_summarizes(board: Whiteboard) -> dict:
    parallel_seconds = time.perf_counter() - board["fanout_started"]
    try:
        result = calculate_budget(board["data"])
        calculation = (
            f"Python total spending: {result['total_spending']} {result['base_currency']} | "
            f"budget: {result['budget']} {result['base_currency']} | "
            f"budget remaining: {result['budget_remaining']} {result['base_currency']} | "
            f"actual savings: {result['actual_savings']} {result['base_currency']} | "
            f"savings goal: {result['savings_goal']} {result['base_currency']}"
        )
        fx_required = len(currencies_in(board["data"])) > 1
        decision = "REVIEW REQUIRED" if fx_required and not board["fx_ok"] else result["decision"]
    except (KeyError, TypeError, ValueError) as problem:
        calculation = f"Input could not be safely calculated: {problem}"
        decision = "REVIEW REQUIRED"

    summary = ask(
        "Summarize these specialist notes and the separately computed budget facts in two "
        "short sentences. Do not alter the decision or invent rates. The decision is made by Python.",
        "\n".join(board["findings"] + [calculation, f"Python decision: {decision}"]),
    )
    return {
        "decision": decision,
        "calculation": calculation,
        "summary": summary,
        "parallel_seconds": parallel_seconds,
    }


def build_graph():
    graph = StateGraph(Whiteboard)
    graph.add_node("lead_decides", lead_decides)
    for name, job in LOCAL_SPECIALISTS.items():
        graph.add_node(name, make_local_specialist(name, job))
        graph.add_edge(name, "lead_summarizes")
    graph.add_node("fx", fx_desk)
    graph.add_edge("fx", "lead_summarizes")
    graph.add_node("lead_summarizes", lead_summarizes)
    graph.add_edge(START, "lead_decides")
    graph.add_conditional_edges("lead_decides", send_to_team, list(MENU))
    graph.add_edge("lead_summarizes", END)
    return graph.compile()


def main() -> int:
    global desk_card, why_no_desk
    desk = DEFAULT_DESK
    if "--desk" in sys.argv:
        index = sys.argv.index("--desk")
        if index + 1 >= len(sys.argv):
            raise SystemExit("--desk requires a URL")
        desk = sys.argv[index + 1]
    args = [arg for index, arg in enumerate(sys.argv[1:]) if arg != "--desk" and (index == 0 or sys.argv[index] != "--desk")]
    if "--draw" in args:
        print(build_graph().get_graph().draw_mermaid())
        return 0
    names = [arg for arg in args if not arg.startswith("-")]
    name = names[0] if names else "match"
    if name not in INPUTS:
        raise SystemExit(f"Unknown input {name!r}. Choose one of: {', '.join(INPUTS)}")
    data = INPUTS[name]
    print(banner(f"PERSONAL FINANCE CHECK · {name}"))
    print(json.dumps(data, indent=2))

    try:
        card = read_business_card(desk)
        if offers(card, "fx"):
            desk_card = card
            print(f"📇 Read {card.get('name', 'FX Desk')} card; it advertises 'fx'.")
        else:
            why_no_desk = "the card does not advertise the required 'fx' skill"
            print(f"⛔ {why_no_desk}")
    except (urllib.error.URLError, OSError, ValueError) as problem:
        why_no_desk = f"nobody answered at {desk}: {problem}"
        print(f"☎️  No FX desk card at {desk}: {problem}")

    board = build_graph().invoke(
        {"data": data, "findings": [], "timings": [], "failed_specialists": [], "fx_ok": False},
        config={"recursion_limit": 10},
    )
    print("\n📋 THE WHITEBOARD")
    print(indent("\n".join(board["findings"]) or "(nothing)"))
    print(f"\n🧮 {board['calculation']}")
    print(f"🏁 DECISION: {board['decision']} (computed by Python; cross-currency FX failure fails closed)")
    print(indent(board["summary"]))
    print(f"\n⏱  {len(board['team'])} specialist(s): {board['parallel_seconds']:.1f} s parallel; "
          f"{sum(board['timings']):.1f} s sequential")
    expected = (
        "REVIEW REQUIRED"
        if board["decision"] == "REVIEW REQUIRED" and len(currencies_in(data)) > 1
        else EXPECTED[name]
    )
    print(f"\nExpected {expected!r}; got {board['decision']!r}")
    print("\n" + meter.card(
        agents=len(board["team"]) + 1,
        model=setup_env.MODEL,
        note="FX Desk tokens and cost are reported by the desk process, not this manager.",
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())