# Exercise 1 — The Team

**Agents share information by passing a NOTE.** · CrewAI · built together · ~15 minutes

```
   Reviewer ──note──▶ Fixer ──note──▶ Teacher
   finds problems     fixes exactly    explains it
   never fixes        those            to a junior
```

Three agents, one job each. **Each one sees only the notes it is handed.**
In CrewAI the note is one argument on a task:

```python
context=[review_task]      # "you may read what the Reviewer wrote"
```

Context engineering decides what goes into *one* agent's context. `context=[...]`
makes that decision for *each* agent.

---

## Step 0 — run it before you change anything

```powershell
cd ex1-the-team
python team_starter.py
```

About 10 seconds. The starter runs from minute one — it just has two agents
instead of three. You will see:

- `⏳ 2 agent(s) working...`
- the Reviewer's list of problems (usually all three planted bugs)
- `✋ Nobody is fixing anything yet. Do TODO 1 and TODO 2.`
- the Teacher's three bullets — **read them carefully.** Are they about *this*
  code? The Teacher was handed no notes.
- a cost card: agents, LLM calls, tokens, dollars, seconds

---

## TODO 1 — hire the Fixer

Copy the `reviewer = Agent(...)` block, rename it `fixer`, and change three things:

| field | new value |
|---|---|
| `role` | `"Code Fixer"` |
| `goal` | fix exactly the problems it is handed, and nothing else |
| `backstory` | it changes as little as possible |

Keep `llm=setup_env.crew_llm()` — **one model object per agent**, so the cost
meter stays honest.

✅ **Checkpoint:** `⏳ 3 agent(s) working...` — but still nobody fixing. A Fixer
with no work is just a salary. That is TODO 2.

## TODO 2 — give the Fixer its work, and hand it the note

Build `fix_task = Task(...)` with four things:

| argument | value |
|---|---|
| `description` | include the original code with `{code}`, and tell it to fix **only** the problems on the Code Reviewer's list |
| `expected_output` | `"The complete fixed Python code and nothing else."` |
| `agent` | `fixer` |
| `context` | `[review_task]` ← **this is the note being passed** |

✅ **Checkpoint:** under `📝 Fixer ──▶ Teacher` you now see fixed code:
a `?` placeholder in the query, a check for no orders, a `conn.close()`.

## TODO 3 — let the Teacher read the notes

The Teacher's task says `context=[]`. Hand it the **two** notes it needs:
the problems, and the fix.

✅ **Checkpoint:** the Teacher's bullets now talk about *this* code — SQL
injection, dividing by zero, the connection. The `👀` warning is gone.

---

## 🔍 Look closer (this is the lesson)

1. **Before TODO 3, what did the Teacher say?** Ours said the code *"had a typo
   in the variable name"*. There is no typo. An agent without the note does not
   say "I don't know" — it writes something that **sounds** right.
2. **Read the Fixer's code.** When a customer has *no* orders, does it still
   close the connection? (Look at where `return 0` sits.) Now read the
   Teacher's bullet about the connection. Each agent trusted the note it was
   handed; nobody checked the whole thing.
3. **Run one agent doing all three jobs:**
   ```powershell
   python solo_agent.py
   ```
   Put its cost card next to the team's. In our runs the single agent used
   about half the tokens, was faster — and wrapped the connection in
   `try / finally`. On a job this small, one agent was enough.

## Done early?

- `python team_starter.py split_bill` — a different piece of code. Does the team still hold up?
- Add a fourth agent, a **Tester**, that writes three test cases for the fixed
  code. Which notes should it read?

## Fell behind?

Open `team_solution.py` — it has every line we typed together.
