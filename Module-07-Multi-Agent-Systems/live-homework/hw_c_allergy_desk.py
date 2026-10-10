"""
Live homework · Part C -- THE PHONE CALL  ·  the ALLERGY DESK  (server, on your own)

The clinic's dietitians run their own agent. It is built with CrewAI, it lives
in its own program, and it checks menus for ONE thing: allergy risks. You
cannot see its prompt or its memory. The outside world gets two things:

    a card           GET  /.well-known/agent-card.json
    a phone number   POST /       JSON-RPC 2.0, method "SendMessage"

The same protocol as Exercise 3 (A2A v1.0). Your job here is ONE TODO: the card.

Run it in TERMINAL 1 and leave it running:
    python hw_c_allergy_desk.py
Then open its card in your browser:
    http://127.0.0.1:9998/.well-known/agent-card.json

(Port 9998, so it never collides with the Exercise 3 desk on 9999.)
"""

import argparse
import json
import sys
import time
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "shared"))

import setup_env  # noqa: E402  ALWAYS FIRST
from meter import Meter  # noqa: E402

print("⏳ waking up CrewAI (a few seconds)...", flush=True)
from crewai import Agent, Crew, Process, Task  # noqa: E402

CARD_PATH = "/.well-known/agent-card.json"


# ─── 1 · THE CARD ────────────────────────────────────────────────────────────
def agent_card(base_url: str) -> dict:
    return {
        "name": "Allergy Desk",
        "description": "Checks dinner menus for guests' food-allergy risks only; it does not assess dietary needs, budgets, or menu variety.",
        "version": "1.0.0",
        "provider": {"organization": "Clinic Dietitians", "url": "https://clinic.example"},
        "supportedInterfaces": [
            {"url": base_url, "protocolBinding": "JSONRPC", "protocolVersion": "1.0"},
        ],
        "capabilities": {"streaming": False, "pushNotifications": False},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "skills": [
            {
                "id": "allergy-check",
                "name": "Allergy check",
                "description": "Send the dinner request with its menu and guests' allergies; this desk returns allergy risks as BLOCKER or MINOR findings, or NONE.",
                "tags": ["allergy", "food-safety"],
            }
        ],
    }


# ─── THE BRAIN: a CrewAI agent nobody outside ever sees (done for you) ───────
def allergy_check(request: str, meter: Meter) -> str:
    dietitian = Agent(
        role="Clinic Dietitian",
        goal="Find every allergy risk in a menu for the guests who will eat it",
        backstory="You work in a hospital allergy clinic. You check menus against the guests' "
                  "allergies, including hidden ingredients and sauces. Diets, budgets and taste "
                  "are other people's jobs.",
        llm=setup_env.crew_llm(),
        verbose=False,
        max_iter=2,
    )
    task = Task(
        description=(
            "Check this dinner request for allergy risks ONLY:\n\n{request}\n\n"
            "List at most 3, one per line, each starting with BLOCKER: (a guest must not eat it) "
            "or MINOR: (worth a warning). If there are none, reply exactly: NONE"
        ),
        expected_output="Lines starting with BLOCKER: or MINOR:, or the single word NONE.",
        agent=dietitian,
    )
    result = Crew(agents=[dietitian], tasks=[task], process=Process.sequential,
                  verbose=False, tracing=False).kickoff(inputs={"request": request})
    meter.record_crew(result)
    return result.raw.strip()


# ─── 2 · THE REPLY, IN A2A SHAPE (done for you) ──────────────────────────────
def as_a2a_task(answer: str, context_id: str) -> dict:
    return {
        "task": {
            "id": str(uuid.uuid4()),
            "contextId": context_id,
            "status": {"state": "TASK_STATE_COMPLETED",
                       "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds")},
            "artifacts": [{"artifactId": str(uuid.uuid4()), "name": "allergy-check",
                           "parts": [{"text": answer}]}],
        }
    }


def rpc_error(req_id, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


class AllergyDesk(BaseHTTPRequestHandler):
    def _send_json(self, status: int, body: dict) -> None:
        data = json.dumps(body, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _base_url(self) -> str:
        return f"http://{self.headers.get('Host', f'127.0.0.1:{self.server.server_port}')}/"

    def do_GET(self):
        if self.path.split("?")[0] == CARD_PATH:
            print(f"📇 {now()}  someone read our card", flush=True)
            self._send_json(200, agent_card(self._base_url()))
        else:
            self._send_json(404, {"error": f"Nothing here. The card is at {CARD_PATH}"})

    def do_POST(self):
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0) or 0))
        try:
            call = json.loads(raw or b"null")
        except json.JSONDecodeError:
            return self._send_json(200, rpc_error(None, -32700, "Invalid JSON payload"))
        if not isinstance(call, dict) or call.get("jsonrpc") != "2.0" or "method" not in call:
            return self._send_json(200, rpc_error(None, -32600, "Request payload validation error"))
        req_id = call.get("id")
        if call["method"] != "SendMessage":
            return self._send_json(200, rpc_error(req_id, -32601, f"Method not found: {call['method']}"))
        message = (call.get("params") or {}).get("message") or {}
        text = "\n".join(p["text"] for p in message.get("parts", []) if isinstance(p, dict) and "text" in p)
        if not text.strip():
            return self._send_json(200, rpc_error(req_id, -32602, "Invalid parameters: no text part"))

        print(f"📞 {now()}  incoming call · SendMessage · {len(text)} characters", flush=True)
        print("   🩺 our CrewAI dietitian is checking it...", flush=True)
        meter = Meter()
        try:
            answer = allergy_check(text, meter)
        except Exception as exc:
            print(f"   💥 {exc}", flush=True)
            return self._send_json(200, rpc_error(req_id, -32603, "Internal error"))
        context_id = message.get("contextId") or str(uuid.uuid4())
        self._send_json(200, {"jsonrpc": "2.0", "id": req_id, "result": as_a2a_task(answer, context_id)})
        lines = sum(1 for ln in answer.splitlines() if ln.strip().upper().startswith(("BLOCKER", "MINOR")))
        print(f"✅ {now()}  replied TASK_STATE_COMPLETED · {lines} finding(s) · "
              f"{meter.tokens_in + meter.tokens_out} tokens · ${meter.dollars(setup_env.MODEL) or 0:.5f}",
              flush=True)

    def log_message(self, *args):
        pass


def now() -> str:
    return time.strftime("%H:%M:%S")


def main() -> int:
    parser = argparse.ArgumentParser(description="The Allergy Desk: a CrewAI agent served over A2A.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9998)
    args = parser.parse_args()
    try:
        server = HTTPServer((args.host, args.port), AllergyDesk)
    except OSError:
        print(f"\n❌ Port {args.port} is busy. Is the Allergy Desk already running in another terminal?")
        print(f"   Or start it on another port:  python {Path(__file__).name} --port 9997")
        return 1
    shown = "127.0.0.1" if args.host in ("0.0.0.0", "") else args.host
    print("\n🩺 Allergy Desk is open")
    print(f"   card          : http://{shown}:{args.port}{CARD_PATH}   <- open this in your browser")
    print(f"   phone number  : http://{shown}:{args.port}/   (JSON-RPC 2.0, method SendMessage)")
    card = agent_card(f"http://{shown}:{args.port}/")
    if not card.get("description") or not card.get("skills"):
        print("   ⚠️  the card is still blank (TODO 1): no description or no skills.")
        print("      A manager will read it and refuse to send you any menu.")
    print("   waiting for calls...   (Ctrl+C to hang up)\n", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n☎️  hung up.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
