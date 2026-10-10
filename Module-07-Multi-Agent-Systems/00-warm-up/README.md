# Warm-up — two agents talking

> No framework. Nothing hidden. 70 lines of Python.

```
   CODER  ──── its code ────▶  REVIEWER
          ◀── feedback ──────
               (or APPROVED)
```

This is already a complete multi-agent system:

| piece | what it really is |
|---|---|
| two agents | two different **system prompts** — and they know different things |
| talking | passing **strings** back and forth |
| a stop rule | stop at `APPROVED`, or after `MAX_ROUNDS = 3`, no matter what |

Everything else today is this idea, organised.

## Run it

```powershell
cd 00-warm-up
python two_agents_talking.py
```

About 5 seconds. You will see something like this (a real run):

```
🧑‍💻 CODER     def average(numbers): return sum(numbers) / len(numbers) if numbers else 0
🔍 REVIEWER  The function returns 0 for an empty list instead of raising ValueError.
🧑‍💻 CODER     def average(numbers): raise ValueError("List is empty") if not numbers else sum(numbers) / len(numbers)
🔍 REVIEWER  APPROVED

✅ The two agents agreed after 2 round(s).
```

The reviewer knows a team rule the coder was never told: *an empty list must
raise `ValueError`*. That is the point of having two agents — different agents,
different context.

## 🧪 Now check their work

The reviewer approved the final line. Paste it into Python and call it on a
normal list:

```powershell
python
```
```python
>>> def average(numbers): raise ValueError("List is empty") if not numbers else sum(numbers) / len(numbers)
>>> average([2, 4])
```

What happens? Why did two agents both miss it?

<details>
<summary>Answer (open after you have tried)</summary>

```
TypeError: exceptions must derive from BaseException
```

Python reads the line as `raise (ValueError(...) if not numbers else the_average)`.
So it **raises on every list** — on a normal list it tries to raise the number
`3.0`. Both agents read it like English. Neither ran it.

**Two agents agreeing is not proof.** The final say belongs to code: a test, a
check, a rule. You will see this idea in every part of today.
</details>

## Try this (2 minutes each)

1. Set `MAX_ROUNDS = 1`. What does the stop rule print now?
2. Delete the team rule from `REVIEWER`. Does the reviewer still object to `return 0`?
3. Change the task to *"a function median(numbers)"*. Do they agree faster or slower?
