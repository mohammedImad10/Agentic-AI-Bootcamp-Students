# Module 7 — Multi-Agent Systems

*Modules 7, 8 and 9 of the syllabus, in one Saturday.*

> **The one thing to leave with:** agents share information in exactly three
> ways — **they pass a note, they share a whiteboard, or they make a phone
> call.** Pick the right one, and keep the final say in **code**, not in an
> agent's opinion.

An agent is only as good as what goes into its context (*context engineering*).
Today you split a job across several agents, so each one's context holds only
its own job — and you measure whether that was worth it.

---

## Read this before you touch anything

### 1. Use the right Python

Same environment as Module 2. **Python 3.12.** From the repo root:

```powershell
.\Module-02\.venv\Scripts\Activate.ps1          # Windows PowerShell
source Module-02/.venv/bin/activate             # macOS / Linux
```

Your prompt now starts with `(.venv)`. If PowerShell says *running scripts is
disabled*, run `Set-ExecutionPolicy -Scope Process RemoteSigned` and activate again.

### 2. Install

**Nothing new.** Same packages, same versions as Module 2. A2A (Part 3) is plain
HTTP, built into Python. Only if the preflight says something is missing:

```powershell
python -m pip install -r Module-07-Multi-Agent-Systems\requirements.txt
```

### 3. Your `.env`

`OPENROUTER_API_KEY` at the repo root. Same key as always.

### 4. Setup check

```powershell
cd Module-07-Multi-Agent-Systems
python preflight.py
```

Every line should say `[ OK ]` and end with **All clear.** A red line? Fix it
now, not in Part 3. The preflight tells you exactly what to do.

---

## The module, in order

**First half — together.** We build each exercise live; you type along.

| # | folder | what we build | shares information by… | time |
|---|---|---|---|---|
| 0 | **`00-warm-up/`** | Two agents talk. No framework. Nothing hidden. | passing strings | 10 min |
| 1 | **`ex1-the-team/`** | A crew of three specialists, one after another (CrewAI). | **passing a note** | 30 min |
| 2 | **`ex2-the-manager/`** | A lead who picks the specialists, who then work at the same time (LangGraph). | **sharing a whiteboard** | 35 min |
| 3 | **`ex3-the-phone-call/`** | Your manager calls another team's agent in another program (A2A). | **making a phone call** | 35 min |

**Second half — on your own.**

| # | folder | what you do | time |
|---|---|---|---|
| ★ | **`live-homework/`** | **The Dinner Party Desk** — the same three moves, alone, on a new problem. Six TODOs. We walk through the solution at the end. | 60 min |
| ▶ | **`mini-project/`** | **This week's mini-project** — your own agent network. | ~3–4 h, during the week |

**Every folder has its own README. That README is your worksheet.**
The full run order, with what you should see at every step, is in
[`M7-Lab-Worksheet.md`](M7-Lab-Worksheet.md).

Each exercise has:

- a **starter** that *runs from minute one* and tells you which TODO is next,
- a few **TODOs**, one idea each,
- a **solution** (for Exercises 1–3) you can open if you fall behind.

The exercises do not depend on each other. If one fights you, you can still do the next.

---

## ▶ This week's mini-project

**[→ mini-project/THE-BRIEF.md](mini-project/THE-BRIEF.md)**

**The Cross-Framework Agent Network** — a LangGraph manager and a CrewAI agent
that talk over A2A, for a problem *you* pick. Start from the Exercise 3 solution:
change the domain, keep the plumbing. Ten scenarios are waiting in
[`mini-project/SCENARIOS.md`](mini-project/SCENARIOS.md) if you want one.

**Due before Friday's session.** Submit it as a GitHub issue (the brief shows how).

---

Also here:

- [`M7-Learner-Handout.md`](M7-Learner-Handout.md) — the concepts, written down, with the numbers we measured.
- [`M7-Lab-Worksheet.md`](M7-Lab-Worksheet.md) — the run order, the checkpoints, what "done" looks like.
- `shared/` — code every exercise imports. You never need to edit it.
- `preflight.py` — the setup check. Run it again any time something feels wrong.

---

## The four-hour shape

| time | what |
|---|---|
| 0:00 – 0:25 | What goes into an agent's context (context engineering) — and a job too big for one context · setup check |
| 0:25 – 0:35 | **Warm-up** · two agents talking (`00-warm-up/`) |
| 0:35 – 1:05 | **Part 1** · the team — pass a note (`ex1-the-team/`), built together |
| 1:05 – 1:40 | **Part 2** · the manager — share a whiteboard (`ex2-the-manager/`), built together |
| 1:40 – 1:45 | stretch |
| 1:45 – 2:20 | **Part 3** · the phone call — A2A between two programs (`ex3-the-phone-call/`), built together |
| 2:20 – 2:30 | break |
| 2:30 – 3:30 | **Live homework** · the Dinner Party Desk, on your own (`live-homework/`) |
| 3:30 – 3:50 | Solution walkthrough |
| 3:50 – 4:00 | Which pattern when · where skills fit · this week's mini-project |

---

## When something breaks

| symptom | cause | fix |
|---|---|---|
| `OPENROUTER_API_KEY not found` | no `.env`, or it is not in the repo root | same `.env` as Module 1, at the repo root |
| `ModuleNotFoundError: crewai` (or `langgraph`) | wrong Python — usually a **new terminal** without the venv | activate `Module-02\.venv` in *that* terminal |
| VS Code's **Run ▶** button says `ModuleNotFoundError: crewai` | VS Code picked a different Python (often a `.venv` at the repo root) | `Ctrl+Shift+P` → **Python: Select Interpreter** → `Module-02\.venv` — or run from the terminal instead |
| `running scripts is disabled on this system` | PowerShell execution policy | `Set-ExecutionPolicy -Scope Process RemoteSigned`, then activate again |
| CrewAI asks about *execution traces* and waits 20 s | a script imported `crewai` before `setup_env` | keep `import setup_env` as the first import — every exercise already does |
| `InvalidUpdateError: At key 'findings'` | two specialists wrote to the whiteboard in the same step | that is Exercise 2, TODO 2 working. **TODO 3 is the fix.** |
| `Port 9999 is busy` | the Security Desk is already running in another terminal | use that one, or start a second with `--port 9998` and call it with `--desk http://127.0.0.1:9998` |
| `No answer at http://127.0.0.1:9999` | the Security Desk is not running | start it in Terminal 1 first, then run the manager in Terminal 2 |
| The manager refuses to send code to the desk | the business card has no `security` skill yet | Exercise 3, TODO 1 |
| Windows asks about the firewall | you started the desk with `--host 0.0.0.0` | allow it on *private* networks only, or drop `--host` and stay on `127.0.0.1` |
| Garbled `â€"` in the terminal | Windows console encoding | already fixed in `shared/setup_env.py`; import it first in your own scripts |
| A run costs more than you expected | each agent is its own LLM call | read the cost card printed at the end of every run — that is the point of it |

---

## What we are *not* doing today

We are not installing the official A2A SDK. It is real, it is good, and it
brings a web framework with it. Today you build both sides of the protocol with
Python's standard library, so you can see every byte that crosses the wire.
Once you have seen that, the SDK is just convenience.

We are also not building agent swarms, or agents that negotiate forever.
Every system today has a stop rule, and so should yours.
