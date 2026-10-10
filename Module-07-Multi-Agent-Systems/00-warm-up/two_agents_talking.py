"""
Warm-up  --  two agents talking.  No framework.  Nothing hidden.

This is already a complete multi-agent system:

    two agents   =  two different system prompts (and they know different things)
    talking      =  passing strings back and forth
    a stop rule  =  stop at APPROVED, or after MAX_ROUNDS no matter what

Everything else today is this idea, organised.

Run:
    python two_agents_talking.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "shared"))

import setup_env  # noqa: E402  (always first: key, UTF-8)
from openai import OpenAI  # noqa: E402

client = OpenAI(base_url=setup_env.BASE_URL, api_key=setup_env.API_KEY)

MAX_ROUNDS = 3  # the stop rule. Without it, two polite agents can talk forever.

CODER = (
    "You are a Python developer. Reply with ONE line of Python code only. "
    "No explanation, no backticks."
)
# The reviewer knows a team rule the coder has never been told.
# Different agents, different context: that is the whole point of having two.
REVIEWER = (
    "You are a strict code reviewer. Team rule: a function given an empty list must "
    "raise ValueError. Returning 0 or None, or crashing with ZeroDivisionError, all break "
    "the rule. If the code has a bug or breaks the rule, name the single most important "
    "problem in one short sentence. If the code is correct, reply exactly: APPROVED"
)


def agent(system_prompt: str, message: str) -> str:
    """An agent in its simplest form: instructions + a message in, text out."""
    reply = client.chat.completions.create(
        model=setup_env.MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message},
        ],
    )
    return reply.choices[0].message.content.strip()


task = "Write a function average(numbers) that returns the mean of a list of numbers."

code = agent(CODER, task)
print(f"\n🧑‍💻 CODER     {code}")

for round_number in range(1, MAX_ROUNDS + 1):
    feedback = agent(REVIEWER, code)
    print(f"🔍 REVIEWER  {feedback}")
    if feedback.upper().startswith("APPROVED"):
        print(f"\n✅ The two agents agreed after {round_number} round(s).")
        break
    code = agent(
        CODER,
        f"{task}\nYour previous attempt:\n{code}\nThe reviewer says: {feedback}\nFix it.",
    )
    print(f"🧑‍💻 CODER     {code}")
else:
    print(f"\n⏹  Stopped after {MAX_ROUNDS} rounds without agreement. That is the stop rule working.")
