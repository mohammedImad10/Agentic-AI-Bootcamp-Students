"""
Module 7 -- preflight check.  Run this BEFORE Saturday.
It changes nothing. It only reports, and tells you how to fix what it finds.

    python preflight.py

Today needs NOTHING new: the same environment you built in Module 2
(Python 3.12, CrewAI, LangGraph). A2A is plain HTTP, built into Python.
"""

import importlib.metadata as md
import socket
import sys
import time
from pathlib import Path

TESTED = {
    "openai": "2.52.0",
    "langgraph": "1.2.10",
    "langchain-openai": "1.4.1",
    "crewai": "1.15.10",
    "python-dotenv": "1.2.2",
}
OK, WARN, BAD = "[ OK ]", "[WARN]", "[FAIL]"
HERE = Path(__file__).resolve().parent
problems: list[str] = []


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print("=" * 64)
    print(" Agentic AI Bootcamp - Module 7 (Multi-Agent Systems) preflight")
    print("=" * 64)

    major, minor = sys.version_info[:2]
    if (major, minor) in [(3, 12), (3, 13)]:
        print(f"{OK} Python {sys.version.split()[0]}")
    else:
        print(f"{BAD} Python {sys.version.split()[0]} - CrewAI needs 3.12 or 3.13")
        problems.append("Use the Module 2 environment:  Module-02\\.venv\\Scripts\\python.exe preflight.py")

    in_venv = sys.prefix != sys.base_prefix
    print(f"{OK if in_venv else WARN} virtual environment: {'active' if in_venv else 'NOT active'}")
    if not in_venv:
        problems.append("Activate the Module 2 environment first:  .\\Module-02\\.venv\\Scripts\\Activate.ps1")

    print("-" * 64)
    for package, expected in TESTED.items():
        try:
            found = md.version(package)
        except md.PackageNotFoundError:
            print(f"{BAD} {package:<18} not installed")
            problems.append(f"pip install -r requirements.txt   (missing {package})")
            continue
        flag = OK if found == expected else WARN
        note = "" if found == expected else f"   (class tested on {expected})"
        print(f"{flag} {package:<18} {found}{note}")

    print("-" * 64)
    sys.path.insert(0, str(HERE / "shared"))
    try:
        import setup_env  # noqa: F401  (loads .env, silences CrewAI's first-run question)
        print(f"{OK} shared/setup_env.py loaded, model = {setup_env.MODEL}")
    except SystemExit as stop:  # setup_env exits with a clear message when the key is missing
        print(f"{BAD} {str(stop).strip()}")
        problems.append("Put OPENROUTER_API_KEY=sk-or-... in the .env file at the repo root.")
        return report()

    started = time.perf_counter()
    try:
        from crewai import Agent, Crew, Process, Task  # noqa: F401
        print(f"{OK} CrewAI imports   ({time.perf_counter() - started:.1f} s, no 20-second question)")
    except Exception as exc:
        print(f"{BAD} CrewAI import failed: {exc}")
        problems.append("CrewAI did not import: are you on Python 3.12 in the Module 2 venv?")
    try:
        from langgraph.graph import StateGraph  # noqa: F401
        print(f"{OK} LangGraph imports")
    except Exception as exc:
        print(f"{BAD} LangGraph import failed: {exc}")
        problems.append("LangGraph did not import: pip install -r requirements.txt")

    try:
        reply = setup_env.graph_llm().invoke("Reply with exactly: READY")
        print(f"{OK} OpenRouter answered: {reply.content.strip()!r}")
    except Exception as exc:
        print(f"{BAD} OpenRouter call failed: {str(exc)[:120]}")
        problems.append("Check your key and credit at https://openrouter.ai/keys")

    with socket.socket() as probe:
        busy = probe.connect_ex(("127.0.0.1", 9999)) == 0
    print(f"{WARN if busy else OK} port 9999 {'is BUSY (something is already using it)' if busy else 'is free for the Security Desk'}")
    if busy:
        problems.append("Port 9999 is taken. In Exercise 3 start the desk with  --port 9998")

    return report()


def report() -> int:
    print("=" * 64)
    if problems:
        print(f"{len(problems)} thing(s) to fix before Saturday:\n")
        for number, fix in enumerate(problems, 1):
            print(f"  {number}. {fix}")
        print("\nStuck? Post this whole output in the class channel.")
        return 1
    print("All clear. You are ready for Saturday.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
