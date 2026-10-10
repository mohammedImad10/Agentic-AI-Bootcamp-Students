<!-- JHF-BRAND -->
<div align="center" style="padding:28px 20px; background:#ffffff; border:2px solid #e0e0e0; border-radius:12px;">
  <p style="margin:0 0 16px 0;">
    <img src="../assets/jhf-logo.png" alt="Jerusalem High-Tech Foundry (JHF)" height="54" style="vertical-align:middle; margin:0 22px;" />
    <img src="../assets/comcec-logo.png" alt="COMCEC - Cooperation for Development" height="72" style="vertical-align:middle; margin:0 22px;" />
  </p>
  <h1 style="color:#1a3c5e; margin:6px 0;">Agentic AI Bootcamp</h1>
  <h3 style="color:#0078d4; margin:4px 0; font-weight:600;">Module 7 &middot; Lab Worksheet &mdash; Multi-Agent Systems</h3>
  <hr style="border:0; border-top:1px solid #0078d4; width:60%; margin:16px auto;" />
</div>

# M7 Lab — the run order

> **Goal:** build three small multi-agent systems **together** — a team that
> passes notes, a manager with a shared whiteboard, and two programs that talk
> over A2A — then do the same three moves **on your own** in the live homework.
>
> **Time:** first half together (~1 h 45), second half on your own (60 min) + the solution walkthrough.
> **You need:** the Module 2 environment + `OPENROUTER_API_KEY` in `.env`. Nothing new to install.

**Every exercise folder has its own README — that README is your worksheet for
that exercise.** This page is the order to do them in, and how to know you are done.

---

## Setup gate (5 min)

From the repo root:

```powershell
git pull
.\Module-02\.venv\Scripts\Activate.ps1
cd Module-07-Multi-Agent-Systems
python preflight.py
```

✅ Every line `[ OK ]` and **All clear** → you are ready.
❌ Anything else → the preflight prints the fix. Do it now, not in Part 3.

---

## Warm-up — two agents talking (10 min, together) · `00-warm-up/`

```powershell
cd 00-warm-up
python two_agents_talking.py
```

🧪 **Checkpoint.** The two agents agree. Paste their final line into Python and
call `average([2, 4])`. Did they agree on something that works?

---

## Part 1 — The Team (together) · `ex1-the-team/`

Pass a note. Follow **[`ex1-the-team/README.md`](ex1-the-team/README.md)**.

| run after… | you should see |
|---|---|
| nothing (Step 0) | 2 agents · `✋ Nobody is fixing anything yet` · a Teacher explaining code it never saw |
| TODO 1 — hire the Fixer | `3 agent(s) working` · still nobody fixing |
| TODO 2 — `context=[review_task]` | fixed code under `📝 Fixer ──▶ Teacher` |
| TODO 3 — the Teacher reads both notes | three bullets about *this* code · the `👀` warning is gone |

🧪 **Checkpoint.** Run `python solo_agent.py` and put its cost card next to the
team's. Which was cheaper? Which closed the database connection on every path?

---

## Part 2 — The Manager (together) · `ex2-the-manager/`

Share a whiteboard. Follow **[`ex2-the-manager/README.md`](ex2-the-manager/README.md)**.

| run after… | you should see |
|---|---|
| nothing (Step 0) | `Lead chose: correctness` although the model asked for four |
| TODO 1 — code decides the team | `Lead chose: correctness, security, performance` · `👀 … only 1 worked. That is TODO 2.` |
| TODO 2 — return the whole team | `💥 CRASH -- and this one is on purpose.` |
| TODO 3 — `Annotated[list[str], operator.add]` | three specialists on the whiteboard · `VERDICT: BLOCK` · parallel faster than one-after-another |

🧪 **Checkpoint.** Run it on `split_bill`. Which specialists did the lead pick?
Which planted bug did *nobody* find?

---

## Part 3 — The Phone Call (together) · `ex3-the-phone-call/`

Make a phone call. **Two terminals.** Follow **[`ex3-the-phone-call/README.md`](ex3-the-phone-call/README.md)**.

| terminal | command |
|---|---|
| 1 — the Security Desk | `python security_desk_starter.py` (leave it running) |
| 2 — the manager | activate the venv **again**, then `python manager_a2a_starter.py` |

| run after… | you should see |
|---|---|
| nothing (Step 0) | `⛔ the card does not advertise a 'security' skill` · the verdict is still BLOCK |
| TODO 1 — the CARD | `✅ it offers a 'security' skill` · then *the desk refused the call … (TODO 2?)* |
| TODO 2 — the MESSAGE | Terminal 1: `📞 incoming call` … `✅ replied TASK_STATE_COMPLETED` |
| TODO 3 — the TASK | Terminal 2: `📞 security answered with N line(s) … over A2A` |

🧪 **Checkpoint.** Stop the desk with **Ctrl+C** and run the manager again.
What is the verdict — and why is that the only safe answer?

---

# Second half — on your own

## Live homework — the Dinner Party Desk (60 min) · `live-homework/`

The same three moves, alone, on a new problem: a dinner party with an allergy,
two vegetarians and a budget. Follow **[`live-homework/README.md`](live-homework/README.md)**.
Six TODOs, two per part. **No solution files** — we walk through them together at the end.

| part | run after all TODOs, you should see |
|---|---|
| **A · The Team** (15 min) | `New menu check: ✅ no peanut sauce ✅ a vegetarian main ✅ within budget`, and an invitation that names the real dishes |
| **B · The Manager** (20 min) | the party gets `allergy, diet, budget` · `3/3` planted problems · the picnic gets a smaller team |
| **C · The Phone Call** (25 min) | desk running → `[allergy·A2A] BLOCKER` · desk stopped → still `CHANGE THE MENU` |

Each part stands alone. Stuck for 5 minutes on one TODO? Move to the next part and come back.

---

## If you finish early

Pick one:

- **Exercise 1:** add a fourth agent, a *Tester*, that writes three test cases. Which notes does it need?
- **Exercise 2:** add a `"tests"` specialist to the `SPECIALISTS` dictionary and watch the lead start hiring it.
- **Exercise 3:** call a classmate's desk across the room (`--host 0.0.0.0` on theirs, `--desk http://THEIR-IP:9999` on yours).
- **Any time:** start reading [`mini-project/THE-BRIEF.md`](mini-project/THE-BRIEF.md) and pick your scenario.

---

## Exit ticket (before you leave)

Write one or two sentences for each:

1. Your Teacher agent explains code it never saw. What is missing?
2. Two specialists write `findings` in the same step. What happens — and what is the fix?
3. The Security Desk does not answer. What should your manager's verdict be — and why?

---

## Stuck?

1. Read what the starter printed. Every stage tells you which TODO is next.
2. Check the **When something breaks** table in [`README.md`](README.md).
3. Exercises 1–3: fell behind? Open the `_solution.py` next to the starter.
   Live homework: use Exercises 1–3 as your reference — the moves are the same.
4. Still stuck → hand up, or post the **whole** terminal output in the class channel.

---

<div align="center" style="padding:14px; border-top:2px solid #0078d4; margin-top:34px;">
  <p style="color:#888; font-size:13px; margin:0;">
    <strong>JHF Agentic AI Bootcamp</strong> &mdash; Module 7 Lab Worksheet<br/>
    Organized by Jerusalem High-Tech Foundry (JHF) &middot; In partnership with COMCEC
  </p>
</div>
