"""CrewAI FX specialist exposed as a small A2A JSON-RPC service."""

import argparse
import json
import sys
import time
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "shared"))

import setup_env  # noqa: E402  ALWAYS FIRST
from meter import Meter  # noqa: E402

print("⏳ waking up CrewAI...", flush=True)
from crewai import Agent, Crew, Process, Task  # noqa: E402

CARD_PATH = "/.well-known/agent-card.json"


def agent_card(base_url: str) -> dict:
    return {
        "name": "FX Desk",
        "description": "Explains cross-currency budget conversions using the fixed assumptions supplied by the caller; does not provide live rates or financial advice.",
        "version": "1.0.0",
        "provider": {"organization": "Personal Finance Check exercise", "url": "https://example.invalid"},
        "supportedInterfaces": [
            {"url": base_url, "protocolBinding": "JSONRPC", "protocolVersion": "1.0"},
        ],
        "capabilities": {"streaming": False, "pushNotifications": False},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "skills": [
            {
                "id": "fx-budget-note",
                "name": "FX budget note",
                "description": "Send a monthly budget and explicit fixed exercise rates. Get one FX_NOTE line explaining the assumptions and why real rates and fees must be verified.",
                "tags": ["fx", "currency", "budget"],
                "examples": ["Explain an EUR expense converted to a USD budget using caller-supplied illustrative rates."],
            }
        ],
    }


def fx_review(message: str, meter: Meter) -> str:
    specialist = Agent(
        role="Foreign Exchange Context Specialist",
        goal="Explain the supplied fixed currency assumptions and their limitations without inventing live rates",
        backstory="You work at an independent FX desk. You never claim to know today's rate, never replace the caller's fixed assumptions, and never make the budget decision.",
        llm=setup_env.crew_llm(),
        verbose=False,
        max_iter=2,
    )
    task = Task(
        description=(
            "Review the supplied budget and rate assumptions. Do not recalculate the budget or decide whether it is on track. "
            "Do not invent rates. Return exactly one concise line starting FX_NOTE: that says the supplied rates are illustrative, "
            "not live quotes, and that actual rates and fees should be checked.\n\n{message}"
        ),
        expected_output="Exactly one line beginning FX_NOTE: with an explicit warning that the rates are illustrative, not live quotes.",
        agent=specialist,
    )
    result = Crew(agents=[specialist], tasks=[task], process=Process.sequential,
                  verbose=False, tracing=False).kickoff(inputs={"message": message})
    meter.record_crew(result)
    return result.raw.strip()


def as_a2a_task(answer: str, context_id: str) -> dict:
    return {
        "task": {
            "id": str(uuid.uuid4()),
            "contextId": context_id,
            "status": {
                "state": "TASK_STATE_COMPLETED",
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            },
            "artifacts": [
                {"artifactId": str(uuid.uuid4()), "name": "fx-budget-note", "parts": [{"text": answer}]}
            ],
        }
    }


def rpc_error(request_id, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


class FXDesk(BaseHTTPRequestHandler):
    def _send_json(self, status: int, body: dict) -> None:
        data = json.dumps(body, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _base_url(self) -> str:
        host = self.headers.get("Host", f"127.0.0.1:{self.server.server_port}")
        return f"http://{host}/"

    def do_GET(self):
        if self.path.split("?")[0] == CARD_PATH:
            print(f"📇 {time.strftime('%H:%M:%S')} someone read our FX card", flush=True)
            self._send_json(200, agent_card(self._base_url()))
        else:
            self._send_json(404, {"error": f"The FX card is at {CARD_PATH}"})

    def do_POST(self):
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0) or 0))
        try:
            call = json.loads(raw or b"null")
        except json.JSONDecodeError:
            return self._send_json(200, rpc_error(None, -32700, "Invalid JSON payload"))
        if not isinstance(call, dict) or call.get("jsonrpc") != "2.0" or "method" not in call:
            return self._send_json(200, rpc_error(None, -32600, "Invalid request"))
        request_id = call.get("id")
        if call["method"] != "SendMessage":
            return self._send_json(200, rpc_error(request_id, -32601, "Method not found"))

        message = (call.get("params") or {}).get("message") or {}
        text = "\n".join(part["text"] for part in message.get("parts", [])
                          if isinstance(part, dict) and "text" in part)
        if not text.strip():
            return self._send_json(200, rpc_error(request_id, -32602, "No text part"))

        print(f"📞 {time.strftime('%H:%M:%S')} SendMessage · {len(text)} characters", flush=True)
        meter = Meter()
        try:
            print("   🤖 CrewAI FX specialist is reviewing...", flush=True)
            answer = fx_review(text, meter)
            if not any(line.strip().upper().startswith("FX_NOTE:") for line in answer.splitlines()):
                raise ValueError("CrewAI did not return the required FX_NOTE line")
        except Exception as problem:  # noqa: BLE001
            print(f"   💥 {problem}", flush=True)
            return self._send_json(200, rpc_error(request_id, -32603, "FX review failed"))

        context_id = message.get("contextId") or str(uuid.uuid4())
        self._send_json(200, {"jsonrpc": "2.0", "id": request_id,
                              "result": as_a2a_task(answer, context_id)})
        cost = meter.dollars(setup_env.MODEL)
        print(f"✅ TASK_STATE_COMPLETED · {meter.calls} LLM call(s) · "
              f"{meter.tokens_in + meter.tokens_out} tokens · ${cost or 0:.5f} · {meter.seconds():.1f} s",
              flush=True)

    def log_message(self, *args):
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description="CrewAI FX specialist served over A2A")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9999)
    args = parser.parse_args()
    try:
        server = HTTPServer((args.host, args.port), FXDesk)
    except OSError:
        print(f"Port {args.port} is busy; choose another with --port 9998")
        return 1
    shown = "127.0.0.1" if args.host == "0.0.0.0" else args.host
    print(f"\nFX Desk is open: http://{shown}:{args.port}{CARD_PATH}", flush=True)
    print("Waiting for A2A calls (Ctrl+C to stop).\n", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nFX Desk stopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())