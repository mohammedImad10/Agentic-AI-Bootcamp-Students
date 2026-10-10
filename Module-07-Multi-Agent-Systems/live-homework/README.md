# Live Homework — The Dinner Party Desk

**On your own · 60 minutes · second half of the session.**
At the end we walk through the solution together.

You just built three multi-agent systems **together**. Now you do the same three
moves **alone**, on a new problem: planning a dinner party for guests with an
allergy, special diets and a budget.

| part | the move | you did it together in | TODOs | time |
|---|---|---|---|---|
| **A · The Team** | pass a note (CrewAI) | Exercise 1 | 2 | 15 min |
| **B · The Manager** | share a whiteboard (LangGraph) | Exercise 2 | 2 | 20 min |
| **C · The Phone Call** | call another program's agent (A2A) | Exercise 3 | 2 | 25 min |

**Six TODOs in total.** Each part stands alone: stuck on one part, move to the next.

### The rules

1. **On your own.** Your notes and Exercises 1–3 are allowed — they are the best
   reference you have. The solutions are not here yet: we walk through them at the
   end of the session, and they appear in `solutions/` that same evening.
2. **Run the file first, and after every TODO.** Every file tells you what to do next.
3. **Stuck for 5 minutes on one TODO?** Move to the next part and come back.

```powershell
cd live-homework          # from Module-07-Multi-Agent-Systems
```

---

## Part A — The Team (15 min) · `hw_a_the_team.py`

```
   Planner ──note──▶ Chef ──note──▶ Host
   finds problems    fixes exactly   writes the invitation
                     those
```

```powershell
python hw_a_the_team.py
```

**First run, before any TODO:** read what the Chef and the Host wrote. The Chef
sees **only the menu** — nobody told it about Sara. The Host was handed nothing
at all. Is that food on *your* menu?

| TODO | what | the move from Exercise 1 |
|---|---|---|
| 1 | hand the Chef the Planner's note | `context=[...]` on `fix_task` |
| 2 | let the Host read both notes | `context=[...]` on `invite_task` |

✅ **Done when** the last lines say `New menu check: ✅ no peanut sauce ✅ a vegetarian main ✅ within budget`
and the invitation names dishes that are really on the new menu.

## Part B — The Manager (20 min) · `hw_b_the_manager.py`

```
   request ──▶ HEAD PLANNER ──▶ allergy │ diet │ budget │ variety ──▶ HEAD PLANNER ──▶ verdict
               decides who works   (the chosen ones, all at once)        reads the board
```

```powershell
python hw_b_the_manager.py
```

**First run:** the model asks for three specialists; your code sends only one.

| TODO | what | the move from Exercise 2 |
|---|---|---|
| 1 | the model REQUESTS a team, your code DECIDES | split · keep real names · budget · never nobody |
| 2 | send the work to the whole team — **and** give `findings` its merge rule | a **list** + `Annotated[list[str], operator.add]` |

✅ **Done when** the party gets `allergy, diet, budget`, finds `3/3` planted
problems, and the timing line shows parallel faster than one-after-another.
Then `python hw_b_the_manager.py picnic` — the head planner should pick a
**smaller** team.

## Part C — The Phone Call (25 min) · two terminals

The clinic's dietitians run an **Allergy Desk**: a CrewAI agent in its own
program, on port **9998**. Your manager checks diet, budget and variety itself,
and **phones** the clinic for allergies.

> A guest's allergy is medical information, so **only the clinic's desk receives
> it**. Your local specialists see the menu, the budget and the diets — nothing
> more. Each agent gets only what its job needs.

**Terminal 1:**

```powershell
python hw_c_allergy_desk.py
```

**Terminal 2** — a new terminal needs the venv again (from the repo root):

```powershell
.\Module-02\.venv\Scripts\Activate.ps1
cd Module-07-Multi-Agent-Systems\live-homework
python hw_c_manager.py
```

**First run:** read the verdict. Would you serve this dinner to Sara?

| TODO | what | where |
|---|---|---|
| 1 | write the Allergy Desk's **card**: a description and one skill tagged `allergy` | `hw_c_allergy_desk.py` (then restart the desk) |
| 2 | **fail closed**: if the allergy check could not happen, write a `BLOCKER:` line on the whiteboard | `hw_c_manager.py`, in `allergy_desk()` |

✅ **Done when both are true:**

1. Desk running → `📞 allergy answered … over A2A`, an `[allergy·A2A] BLOCKER` about the peanut sauce, and `VERDICT: CHANGE THE MENU`.
2. Desk stopped (**Ctrl+C** in Terminal 1) → still `VERDICT: CHANGE THE MENU`, with a line saying the allergy check could not be done.

---

## Done early?

- **Part A:** `python hw_a_the_team.py picnic` — does the team handle a request with one problem?
- **Part B:** add a `halal` specialist to `SPECIALISTS`. You do not touch the graph.
- **Part C:** open `http://127.0.0.1:9998/.well-known/agent-card.json` in your browser and read your card the way a stranger would. Would you trust this desk with a guest's health?
- **Any part:** start picking your mini-project scenario — [`../mini-project/SCENARIOS.md`](../mini-project/SCENARIOS.md).
