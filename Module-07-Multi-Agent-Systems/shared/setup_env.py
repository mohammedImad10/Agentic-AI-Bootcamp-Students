"""
shared/setup_env.py  --  every exercise imports this FIRST.

You never need to edit this file. It does four boring jobs so the exercise
files can stay about multi-agent systems:

  1. makes the Windows terminal print emoji and arrows instead of  â€"
  2. stops CrewAI freezing for 20 seconds to ask about "execution traces"
  3. finds your .env and checks OPENROUTER_API_KEY is in it
  4. gives both frameworks (CrewAI and LangGraph) the same model

Why job 2 exists: CrewAI decides "is this your first run?" the moment it is
imported, and it remembers the answer per FOLDER. Every new exercise folder
counts as a first run, so without this you would get a 20-second question in
every folder today. Recording the answer before the import stops it.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# 1 -- UTF-8 console -----------------------------------------------------------
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# 2 -- CrewAI's first-run question (must run BEFORE crewai is imported) ---------
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
os.environ.setdefault("CREWAI_STORAGE_DIR", "jhf-agentic-bootcamp")
try:
    from crewai_core.user_data import update_user_data  # small import, not crewai itself

    update_user_data({"first_execution_done": True, "trace_consent": False})
except Exception:
    pass  # CrewAI not installed, or a different version: nothing to silence

# 3 -- your key ---------------------------------------------------------------
from dotenv import find_dotenv, load_dotenv  # noqa: E402

load_dotenv(find_dotenv(usecwd=True))
for _parent in Path(__file__).resolve().parents:  # also look above this folder
    if (_parent / ".env").exists():
        load_dotenv(_parent / ".env")
        break

API_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()
if not API_KEY:
    sys.exit(
        "\nOPENROUTER_API_KEY not found.\n"
        "Put a file called .env in the repo root containing:\n"
        "    OPENROUTER_API_KEY=sk-or-...\n"
        "It is the same key you have used since Module 1.\n"
    )

BASE_URL = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

# 4 -- one model for both frameworks --------------------------------------------
# .env may say MODEL=openai/gpt-4o-mini or MODEL=openrouter/openai/gpt-4o-mini.
MODEL = os.environ.get("MODEL", "openai/gpt-4o-mini").strip().removeprefix("openrouter/")


def crew_llm():
    """The model, in the form CrewAI wants it.

    Call this once PER AGENT -- do not share one LLM object between agents.
    CrewAI 1.15 keeps a running token count on the LLM object and adds it up
    once per agent, so a shared object makes a 3-agent crew report 3x its real
    usage (9 calls instead of 3). One object per agent keeps the meter honest.
    """
    from crewai import LLM

    return LLM(model=f"openrouter/{MODEL}", temperature=0, api_key=API_KEY)


def graph_llm():
    """The model, in the form LangGraph / LangChain wants it."""
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(model=MODEL, temperature=0, base_url=BASE_URL, api_key=API_KEY)
