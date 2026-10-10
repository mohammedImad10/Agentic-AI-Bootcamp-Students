# Ten scenarios — pick one

Every scenario has the same shape as Exercise 3:

- a **lead** that picks which specialists this input needs,
- **local specialists** in your LangGraph program,
- **one remote desk**: a CrewAI agent that "belongs to another team", called over A2A,
- a **decision** your *code* makes from the lines on the whiteboard,
- **two inputs** that should make the lead pick **different** teams.

Names in `code font` are the exact specialist names to use: **one lowercase
word each**, because the lead's reply is split on anything that is not a letter.

Difficulty: 🟢 comfortable · 🟡 some work · 🔴 ambitious. Your own idea is welcome — see Step 1 of [THE-BRIEF.md](THE-BRIEF.md).

---

### 1. Job Application Desk 🟢

A candidate pastes a job ad and a short CV. Should they apply?

| | |
|---|---|
| local specialists | `skills` — which required skills the CV clearly shows · `gaps` — which must-haves are missing, and how to close them |
| remote desk | `recruiter` — how a recruiter screens this CV · card tags `recruiting`, `cv-review` |
| decision in code | any `MISSING:` line → **DON'T APPLY YET**, otherwise **APPLY** |
| input A | junior data analyst ad + a CV that covers every must-have → `skills` + `recruiter` |
| input B | senior ML engineer ad + a fresh graduate's CV → `gaps` + `recruiter` |
| watch out | "Power BI **or** Tableau" is met by either one. Tell your agents, or they will report a false MISSING. |

### 2. Trip Planner 🟢

A traveller describes a trip. Is it ready to book?

| | |
|---|---|
| local specialists | `budget` · `itinerary` — is the plan realistic, day by day? |
| remote desk | `safety` — visas, entry rules, safety notes · tags `travel-safety`, `visa` |
| decision in code | any `CHECK:` line → **CHECK FIRST**, otherwise **BOOK IT** |
| input A | a 2-day domestic weekend trip → `budget` + `itinerary` |
| input B | a 10-day trip across two countries → `itinerary` + `safety` |

### 3. News Brief in Arabic 🟡

An English news paragraph becomes a short Arabic brief — but only if it is safe to publish.

| | |
|---|---|
| local specialists | `summary` — 3 bullets in English · `claims` — flags statistics and quotes with no source |
| remote desk | `translator` — returns the brief in Modern Standard Arabic · tags `translation`, `ar` |
| decision in code | any `UNVERIFIED:` line → **HOLD**, otherwise **PUBLISH** |
| input A | a plain announcement with no numbers → `summary` + `translator` |
| input B | a paragraph with an unsourced "73% of users…" claim → `claims` + `translator` |
| watch out | the Windows console can show Arabic reversed. Save the brief to a UTF-8 `.txt` file and open it in VS Code. |

### 4. Study Buddy 🟢

A student pastes a question and their draft answer. Ready to hand in?

| | |
|---|---|
| local specialists | `explainer` — what the question really asks · `misconceptions` — the classic mistakes in this draft |
| remote desk | `grader` — marks the draft against a 3-point rubric · tags `grading`, `rubric` |
| decision in code | any `REVISE:` line → **REVISE**, otherwise **READY** |
| input A | a correct but short answer → `grader` |
| input B | an answer with a classic mistake → `misconceptions` + `grader` |

### 5. Bootcamp Help Desk 🟡

A student posts an error message or a question. Answer it, or send it to a human?

| | |
|---|---|
| local specialists | `setup` — venv, keys, packages, paths · `concepts` — explains the idea behind the question |
| remote desk | `policy` — deadlines, extensions, grading rules · tags `policy`, `deadlines` |
| decision in code | any `ESCALATE:` line → **SEND TO THE INSTRUCTOR**, otherwise **ANSWER** |
| input A | `ModuleNotFoundError: crewai` → `setup` |
| input B | "I was sick, can I submit on Monday?" → `policy` |

### 6. Bug Triage 🟡

A bug report arrives. How urgent is it?

| | |
|---|---|
| local specialists | `reproducer` — are the steps to reproduce complete? · `impact` — who is affected, how badly |
| remote desk | `security` — is this bug a security problem? · tags `security`, `triage` |
| decision in code | any `SECURITY:` line → **P1**; any `BLOCKER:` → **P2**; otherwise **P3** |
| input A | "the logo is blurry on mobile" → `impact` |
| input B | "changing the user id in the URL shows another user's invoice" → `reproducer` + `security` |

### 7. Demo Day Organiser 🟡

A request for an event: date, headcount, needs. Can we confirm it?

| | |
|---|---|
| local specialists | `agenda` — does the schedule fit the time? · `budget` |
| remote desk | `venue` — capacity, equipment, accessibility · tags `venue`, `booking` |
| decision in code | any `CONFLICT:` line → **NEEDS CHANGES**, otherwise **CONFIRM** |
| input A | 20 people, 2 hours, one projector → `agenda` + `venue` |
| input B | 150 people, full day, catering, 3 rooms → `agenda` + `budget` + `venue` |

### 8. Customer Support 🟢

An angry customer email. What do we do?

| | |
|---|---|
| local specialists | `tone` — drafts a calm reply · `refunds` — what the refund policy allows |
| remote desk | `courier` — what probably happened to the parcel · tags `shipping`, `tracking` |
| decision in code | `REFUND:` → **REFUND** · `RESHIP:` → **RESHIP** · otherwise **REPLY ONLY** (first rule that matches wins) |
| input A | "the colour is not what I expected" → `tone` + `refunds` |
| input B | "my parcel is 12 days late and the tracking stopped" → `tone` + `courier` |

### 9. Capstone Scoper 🔴 *(pairs with Friday's capstone scoping)*

A student describes their capstone idea. Go, or narrow it?

| | |
|---|---|
| local specialists | `feasibility` — can one person build it in the time? · `requirements` — multi-agent · MCP · memory · guardrails · evaluation · a deployable entry point |
| remote desk | `mentor` — what a reviewer would push back on · tags `mentoring`, `scope` |
| decision in code | any `NARROW:` line → **NARROW IT**, otherwise **GO** |
| input A | a focused idea that already names its agents and tools → `requirements` + `mentor` |
| input B | "an AI that runs my whole company" → `feasibility` + `mentor` |
| why 🔴 | you are grading your own capstone idea. Be honest with the prompts. |

### 10. Personal Finance Check 🔴

A monthly budget in two currencies. On track, or overspending?

| | |
|---|---|
| local specialists | `spending` — where the money goes · `savings` — progress towards the goal |
| remote desk | `fx` — converts amounts between currencies · tags `fx`, `currency` |
| decision in code | compute the totals **in Python**, not in a prompt: over budget → **OVERSPENDING**, otherwise **ON TRACK** |
| input A | a budget in one currency → `spending` + `savings` |
| input B | income in USD, rent in another currency → `fx` + `spending` |
| why 🔴 | a language model does not know today's exchange rate. Your desk must say so — or use a fixed rate table in code and label it. That is the whole lesson. |

---

**Two or more of you picked the same scenario?** Good. Call each other's
remote desks (`--desk http://THEIR-IP:9999`). If your manager works with
*their* desk, your protocol is right.
