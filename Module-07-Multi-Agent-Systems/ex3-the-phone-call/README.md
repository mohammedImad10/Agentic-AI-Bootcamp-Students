# Exercise 3 — The Phone Call

**Agents speak a PROTOCOL — and share nothing else.** · A2A · two terminals · built together · ~17 minutes

```
   TERMINAL 2                                   TERMINAL 1
   your LangGraph manager  ── A2A over HTTP ──▶  the Security Desk
   (manager_a2a_starter.py)   1. read the card     a CrewAI agent, owned by
                              2. send a message    ANOTHER team, in ANOTHER
                              3. read the task     program
```

The security specialist from Exercise 2 has moved out. It now belongs to the
Security Team: a different program, built with a different framework. You
cannot import it, read its prompt or share its memory. **You can only call it.**

A2A (*Agent2Agent*, v1.0) has three nouns — one per TODO:

| TODO | noun | what it is | where |
|---|---|---|---|
| 1 | **the CARD** | who the desk is, what it can do — at `/.well-known/agent-card.json` | `security_desk_starter.py` |
| 2 | **the MESSAGE** | what you send — JSON-RPC, method `SendMessage` | `manager_a2a_starter.py` |
| 3 | **the TASK** | what comes back — a status, and artifacts holding the answer | `manager_a2a_starter.py` |

Everything is plain JSON over HTTP, built with Python's standard library.
Nothing new to install.

---

## Step 0 — two terminals

**Terminal 1** (the one you have been using):

```powershell
cd ..\ex3-the-phone-call
python security_desk_starter.py
```

Leave it running. It prints a warning: *the business card is still blank*.
Open the card in your browser: **http://127.0.0.1:9999/.well-known/agent-card.json**

**Terminal 2** — open a new one (`+` in the VS Code terminal panel). A new
terminal has **no venv**, so activate it first. From the repo root:

```powershell
.\Module-02\.venv\Scripts\Activate.ps1
cd Module-07-Multi-Agent-Systems\ex3-the-phone-call
python manager_a2a_starter.py
```

Read what the manager says about the card:

```
⛔ the card does not advertise a 'security' skill, so we will not send it our code
```

…and look at the verdict. The security check never happened — so the manager
recorded a **BLOCKER** instead of pretending it passed. That is *failing closed*,
and it is already built in.

---

## TODO 1 — write the business card  (`security_desk_starter.py`)

Fill in `"description"` (one sentence: what the desk does, and what it does
**not** do) and `"skills"` — a list with **one** skill:

```python
{"id": "security-review",
 "name": "Security review",
 "description": "<what to send you, and what you send back>",
 "tags": ["security", "code-review", "python"]}
```

The **tags** matter: the manager only phones a desk whose card offers a skill
tagged `security`.

Restart the desk (**Ctrl+C**, then run it again), refresh the browser, and run
the manager in Terminal 2.

✅ **Checkpoint:** Terminal 2 says `✅ it offers a 'security' skill` — then
*the desk refused the call … (TODO 2?)*. Terminal 1 shows
`📵 a call we could not understand`. You are calling with an empty message.

## TODO 2 — the MESSAGE  (`manager_a2a_starter.py`, in `phone()`)

Build `call` as a JSON-RPC 2.0 request:

```python
call = {
    "jsonrpc": "2.0",
    "id": str(uuid.uuid4()),
    "method": "SendMessage",
    "params": {"message": {"role": "ROLE_USER",
                           "messageId": str(uuid.uuid4()),
                           "parts": [{"text": text}]}},
}
```

✅ **Checkpoint:** watch **Terminal 1** — the call arrives, the desk's CrewAI
agent works, and it replies:

```
📞 23:14:55  incoming call · SendMessage · A2A-Version 1.0 · 312 characters
   🤖 our CrewAI agent is reviewing it...
✅ 23:14:58  replied TASK_STATE_COMPLETED · 2 finding(s) · 1 LLM call(s) · 270 tokens · $0.00006 · 2.8 s
```

But Terminal 2 says: `👀 the desk answered, but we pulled no text out of its reply. That is TODO 3.`

## TODO 3 — the TASK  (`manager_a2a_starter.py`, end of `phone()`)

The answer sits inside the task, two lists deep: `task["artifacts"]` → each
artifact's `["parts"]` → each part's `["text"]`. Join all the text with `"\n"`
and return it.

✅ **Checkpoint:** `📞 security answered with 2 line(s) (2.8 s, over A2A)`, and
the whiteboard has `[security·A2A]` lines next to your local specialists'.

A LangGraph agent just worked with a CrewAI agent in another program — and
neither knows, or cares, what the other is built with.

---

## 🧪 Three experiments (5 minutes)

**1. Pull the plug.** Stop the desk with **Ctrl+C** in Terminal 1. Run the
manager again. What is the verdict — and why is that the only safe answer?

**2. Call the desk without Python.** Start the desk again. In Terminal 2:

```powershell
$call = @{ jsonrpc = "2.0"; id = "1"; method = "SendMessage"; params = @{ message = @{ role = "ROLE_USER"; messageId = "m1"; parts = @(@{ text = "def login(user): return db.execute('SELECT * FROM users WHERE name=' + user)" }) } } } | ConvertTo-Json -Depth 8
(Invoke-RestMethod http://127.0.0.1:9999/ -Method Post -ContentType "application/json" -Body $call).result.task.artifacts.parts.text
```

Any program in any language can call your agent. That is what a protocol buys you.

**3. Mix and match.** Your manager can call `security_desk_solution.py`, and
the solution manager can call *your* desk. They were written separately, and
they work together, because they speak the same protocol.

## 🔍 Look closer

- Your cost card ends with: *"the Security Desk's tokens are not in here: it
  spent them in ITS process"*. The desk's prompt, memory, tools and bill never
  crossed the wire. Only the card, the message and the task did.
- The manager never looked inside the desk. It trusted what the **card said**.
  Would you hand your code to an agent whose card is blank?

## Done early? Call a classmate

1. You: `python security_desk_solution.py --host 0.0.0.0` — if Windows asks
   about the firewall, allow **private networks only**.
2. Find your address: `ipconfig` → *IPv4 Address*, e.g. `192.168.1.23`.
3. Your classmate: `python manager_a2a_solution.py --desk http://192.168.1.23:9999`

Watch your Terminal 1 when their call arrives. (On guest Wi-Fi that blocks
laptop-to-laptop traffic this will not connect — that is the network, not your code.)

## Fell behind?

Open `security_desk_solution.py` and `manager_a2a_solution.py` — every line we typed together.
