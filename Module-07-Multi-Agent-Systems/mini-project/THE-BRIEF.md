# Phase 4 Mini-Project — The Cross-Framework Agent Network

**After Module 7. Budget 3–4 hours. Work alone.**
**Due before Friday's session (Fri 9 Oct).** Graded — mini-projects are 35% of your final mark.

---

## The short version

1. **Pick a problem** — one of the [10 scenarios](SCENARIOS.md), or your own.
2. **Build a small agent network** for it: a LangGraph manager, two or more
   specialists, and **one specialist that is a CrewAI agent in another program,
   reached over A2A.**
3. **Prove it works** — and prove it fails *safely* when the other agent is gone.
4. **Answer honestly:** would one agent have been enough?
5. **Submit a GitHub issue.**

No report, no slides.

> **Change the domain, keep the plumbing.** You already have a working network:
> the Exercise 3 solution. Your job is to point it at a different problem — not
> to rebuild it from nothing.

---

## What you are building

```
   YOUR PROGRAM (LangGraph)                          ANOTHER PROGRAM (CrewAI)
   ┌──────────────────────────────────────┐          ┌──────────────────────────┐
   │ LEAD ──▶ specialist A  (local)       │   A2A    │  your remote desk        │
   │   │  ──▶ specialist B  (local)       │ ───────▶ │  card · message · task   │
   │   │  ──▶ remote desk  (a phone call) │          │                          │
   │   └──▶ LEAD reads the board ──▶ DECISION (made by code)                   │
   └──────────────────────────────────────┘          └──────────────────────────┘
```

### Must have

| # | requirement | where it lives in Exercise 3 |
|---|---|---|
| 1 | **A lead that routes.** The model *requests* a team; **code validates** it against an allowed list, with a budget. | `lead_decides` |
| 2 | **Two or more specialists**, each with **one job** and its own short instructions. | `LOCAL_SPECIALISTS` |
| 3 | **One specialist is a CrewAI agent in its own process, called over A2A** — a real card (description + a skill with tags), `SendMessage`, and a Task with artifacts. | `security_desk_solution.py` + `phone()` |
| 4 | **Shared state that merges safely** when specialists write at the same time. | `Annotated[list[str], operator.add]` |
| 5 | **Code has the final say:** the decision (APPROVE / BLOCK, GO / NO-GO, …) is computed by code, there is a **stop rule**, and the network **fails closed** when the remote agent cannot answer. | `lead_summarizes` · `recursion_limit` · `except` in `security_desk` |

### Bonus (not required, but your capstone will need it)

- One of your specialists uses a **tool over MCP** from Module 5. The capstone
  requires *multi-agent + MCP* — doing it here saves you work next week.
- A **second remote agent** on a second port.
- Your desk answers a **classmate's** manager across the room.

---

## Step 1 — Pick the problem (20 min)

Open **[SCENARIOS.md](SCENARIOS.md)**. Each one tells you the specialists, the
remote desk and its card tags, the decision your code makes, and two test
inputs that should route **differently**.

Your own idea is welcome if it passes three checks:

- there is a **decision** code can compute from the specialists' lines,
- there are at least **two genuinely different jobs** for specialists,
- one specialist naturally belongs to **someone else** (another team, another company).

---

## Step 2 — Copy the plumbing (10 min)

Work **inside** the module folder, so the `shared/` imports keep working:

```powershell
cd Module-07-Multi-Agent-Systems
mkdir my-network
copy ex3-the-phone-call\manager_a2a_solution.py  my-network\manager.py
copy ex3-the-phone-call\security_desk_solution.py my-network\remote_desk.py
```

Run both **before changing anything** (two terminals, as in Exercise 3). If the
copy works, every problem from now on is yours, not the plumbing's.

## Step 3 — Change the domain (2 hours)

**In `remote_desk.py` — the other team's agent:**

- the **card**: `name`, `description`, and the skill's `id`, `name`,
  `description` and `tags`
- the CrewAI agent's `role`, `goal`, `backstory`, and the task's `description`
  and `expected_output`
- keep the reply format: one line per finding, each starting with a fixed word
  (`BLOCKER:` / `MINOR:`, or your own words — but fixed, so code can read them)

**In `manager.py` — your program:**

- `LOCAL_SPECIALISTS` — your specialists' names and jobs. **Each name is one
  lowercase word** (`skills`, not `skills-match`): the lead's reply is split on
  anything that is not a letter, so a name with a hyphen or a capital can never be chosen.
- the tag in `offers(card, "security")` → your remote desk's tag
- the name `security` in `MENU` and in the graph → your remote specialist's name (one word too)
- the lead's instructions in `lead_decides`. Tell it plainly: *do not review the
  input yourself — only choose the specialists — and reply with names only*, and
  give an example reply. Without that, a lead that sees a CV instead of code
  starts reviewing it, and its reply mentions every name.
- the **decision** in `lead_summarizes`
- your inputs: replace `pick_sample(...)` and `check_planted(...)` with two or
  three inputs of your own, and what you **expect** the decision to be for each:

```python
INPUTS   = {"match": "...", "stretch": "..."}
EXPECTED = {"match": "APPLY", "stretch": "DON'T APPLY YET"}
# at the end of main():
print(f"expected {EXPECTED[name]!r}, got {board['decision']!r}")
```

That one line is a tiny evaluation set. It catches a wrong decision on the
first run, instead of on Friday.

> Keep the `[name] ` prefix on every line written to the whiteboard. The
> decision code reads it. And tell every agent what does **not** count, for
> example: *"never write a MISSING: line to say that nothing is missing"*.

## Step 4 — Prove it (45 min)

Save real terminal output. Not a description of it.

1. **Two runs, two routes.** Two inputs where the lead picks a **different
   team**. Both transcripts.
2. **The card.** Open `http://127.0.0.1:9999/.well-known/agent-card.json` and
   save the JSON.
3. **The other side of the call.** The desk's terminal log (Terminal 1) while it answers.
4. **Fail closed.** Stop the desk (Ctrl+C) and run once more. Show the decision.
5. **The cost.** The cost cards from your runs.
6. **The diagram.** Add `--draw` support (copy it from `ex2-the-manager/manager_solution.py`)
   and paste the Mermaid into your README — or photograph a drawing. Either is fine.

## Step 5 — Answer one question honestly (15 min)

In your README, one paragraph:

> **Would one agent have been enough?**

Use your numbers: calls, tokens, dollars, seconds — and what the team caught
that one prompt might not have (or didn't). *"One agent would have been enough,
and here is why"* is a perfectly good answer if your numbers say so.

---

## Submit

Your folder, zipped (**without `.env`**), attached to a new issue in the
Students repo using the **"M7 Mini-Project — The Agent Network"** template.

```
my-network/
  README.md        how to run it · the diagram · the one-agent paragraph
  manager.py       your LangGraph manager
  remote_desk.py   your CrewAI agent behind A2A
  evidence/        run1.txt · run2.txt · fail_closed.txt · card.json · desk_log.txt
```

---

## How it's graded

| | weight | you pass the criterion when |
|---|---|---|
| **It routes** | 20% | two inputs, two different teams — and the choice is validated in code |
| **It talks across frameworks** | 25% | a CrewAI agent in its own process answers over A2A: real card, real `SendMessage`, real Task |
| **Code has the final say** | 20% | the decision is computed by code, a stop rule exists, and fail-closed is demonstrated |
| **The evidence is real** | 20% | pasted transcripts, the card JSON, the desk's log, the cost cards |
| **Honest about cost** | 15% | "would one agent have been enough?" answered with your numbers |

**Pass is 4 of 5 criteria.** Opening an issue early and fixing it later beats a
polished one an hour before the deadline.

---

## If you get stuck

1. **The desk will not start: port busy** → another desk is running. Use it, or `--port 9998` and `--desk http://127.0.0.1:9998`.
2. **`⛔ the card does not advertise …`** → the tag in `offers(card, "...")` does not match your card's tags. Same word, both sides.
3. **The lead hires everybody, every time** → it is doing the job instead of choosing. Look at `(the model said: …)`. Tell it not to review the input, to reply with names only, and give an example reply.
4. **One specialist is never chosen** → its name has a hyphen, a space or a capital. One lowercase word.
5. **The decision is always the same** → print the whiteboard and look: lines lost their fixed first word or the `[name] ` prefix, or an agent writes things like `MISSING: None`.
6. **`InvalidUpdateError`** → a key two specialists write at the same time needs `Annotated[list[...], operator.add]`.
7. **Still stuck** → post the whole terminal output (both terminals) in the class channel before Friday.
