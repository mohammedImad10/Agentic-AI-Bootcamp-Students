# Exercise 2 — The Manager

**Agents share information on a WHITEBOARD.** · LangGraph · built together · ~18 minutes

```
                ┌──────────── the whiteboard (shared state) ────────────┐
  code ──▶ LEAD ──▶ correctness │ security │ performance │ readability ──▶ LEAD ──▶ verdict
        decides    only the ones the lead chose, ALL AT THE SAME TIME     reads the board
        who works
```

In Exercise 1 the order was fixed: Reviewer, then Fixer, then Teacher, every
time. Here a **lead decides at run time** who is needed for *this* code, the
chosen specialists work **in parallel**, and they all write on **one shared
whiteboard**.

Three TODOs, one idea each:

| TODO | idea | in one line |
|---|---|---|
| 1 | **routing** | the model *requests* a team — your code *decides* |
| 2 | **parallel** | return a **list** of names, and they all run at once |
| 3 | **shared state** | give the whiteboard a rule for combining writes |

---

## Step 0 — run it before you change anything

```powershell
cd ..\ex2-the-manager
python manager_starter.py
```

Look at the first line it prints:

```
🧭 Lead chose: correctness     (the model said: 'correctness, security, performance, readability')
```

The model asked for four specialists. Only one worked. Only 1 of the 3 planted
bugs was found. The lead's choice is being ignored.

---

## TODO 1 — the model REQUESTS a team, code DECIDES

`reply` is whatever the model typed. Turn it into `team`, a list that is
**guaranteed** to be safe:

| step | code |
|---|---|
| a. split into words | `re.split(r"[^a-z]+", reply.lower())` |
| b. keep only real names, no duplicates | `w in SPECIALISTS` · `dict.fromkeys(...)` |
| c. never more than the budget | `[:MAX_SPECIALISTS]` |
| d. never nobody | `team or ["correctness"]` |

✅ **Checkpoint:** `🧭 Lead chose: correctness, security, performance` — and
at the bottom: `👀 The lead chose 3 specialist(s) but only 1 worked. That is TODO 2.`

> Why not just trust the model? Because it asked for **four** when the prompt
> said *pick only the relevant ones*. A rule in a prompt is **requested**.
> A rule in code is **guaranteed**. (Module 2 — same lesson.)

## TODO 2 — fan out

In `send_to_team`, return the lead's list — `board["team"]` — instead of
`["correctness"]`. Returning a **list** makes LangGraph run every node in it
at the same time.

✅ **Checkpoint:** 💥 **CRASH — on purpose.**

```
💥 CRASH -- and this one is on purpose.
   At key 'findings': Can receive only one value per step. Use an Annotated key to handle multiple values.
```

Three specialists wrote on the whiteboard at the same moment, and the
whiteboard has no rule for combining their writes. LangGraph refuses rather
than silently keep one and throw the others away. Good.

## TODO 3 — a rule for combining writes

In `class Whiteboard`, look at how `timings` is declared two lines down.
Declare `findings` the same way:

```python
findings: Annotated[list[str], operator.add]
```

`operator.add` means: *add the new lines to the list — don't replace it.*

✅ **Checkpoint:** the whiteboard shows lines from three specialists, a
`VERDICT: BLOCK`, and the timing line:

```
⏱  3 specialist(s) worked in parallel: 3.0 s   (one after another: 7.6 s)
```

Same calls, same cost, less waiting.

---

## 🔍 Look closer

1. **Who decides the verdict?** Find it in `lead_summarizes`. The model writes
   the summary; a line of **code** decides BLOCK or APPROVE.
2. **Run `python manager_starter.py split_bill`.** Pure arithmetic — does the
   lead still hire a security specialist? Now look at the planted-bug line:
   `split_bill(100, 3)` returns three shares of `33.33` = `99.99`. A cent
   vanishes. The correctness specialist was *told* to check amounts that do not
   add up — and in our runs it missed this every time. Specialists find what
   their instructions point at.
3. **Read the whiteboard for `orders`.** Does the performance specialist
   mention SQL injection? It was told to stay in its lane. Another request,
   not a guarantee.

## Done early?

- `python manager_solution.py --draw` — prints your graph as Mermaid. Paste it
  into [mermaid.live](https://mermaid.live) and look at the fan-out.
- Set `MAX_SPECIALISTS = 2`. Which specialist gets dropped for `orders`?
- Add a fifth specialist to the `SPECIALISTS` dictionary — say `"tests"`:
  *"Check ONLY what is untested: list the missing test cases."* You do not touch
  the graph: it is built from the dictionary.

## Fell behind?

Open `manager_solution.py` — it has every line we typed together.
