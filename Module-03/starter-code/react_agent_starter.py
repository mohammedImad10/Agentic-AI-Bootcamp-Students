"""
Module 3 Lab — STARTER
ReAct + Planning agent in LangGraph with STRUCTURED OUTPUTS.

  >>> READ M3-Lab-Brief.md FIRST <<<
  It explains what you are building and why, in ten minutes.
  Then follow M3-Lab-Worksheet.md, which walks these TODOs in order.

WHAT YOU ARE BUILDING
  An agent that WORKS OUT numeric answers instead of guessing them:

      REASON  -> the model reads the question + everything found so far,
                 and decides ONE next move
      ACT     -> your Python runs the tool it asked for (no AI here)
      OBSERVE -> the result is written to state["scratchpad"]
      ... loop until it has enough to answer, or the budget runs out.

  Part 1 (Steps 1-5): that loop, as a LangGraph state graph.
  Part 2 (Steps 6-9): add a planner that breaks the goal into steps first.

THE ONE THING TO REMEMBER
  The model has NO memory between calls. It only knows what you put in the
  prompt. state["scratchpad"] IS the memory - if something isn't in there,
  the model cannot see it.

Fill in the TODOs. No manual JSON parsing — use with_structured_output().
Set your key in .env (OPENROUTER_API_KEY=sk-or-...).
"""

import os
import re
from typing import TypedDict, Literal, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

load_dotenv()

MAX_STEPS = 8
MAX_REPLANS = 5


# ---------------------------------------------------------------------------
# Tool: calculator (reuse M1 — safe, returns error string instead of raising)
# ---------------------------------------------------------------------------
_ALLOWED = re.compile(r"^[0-9+\-*/().\s]+$")

def calculator(expr: str) -> str:
    """Safely evaluate a simple arithmetic expression."""
    if not expr or not _ALLOWED.fullmatch(expr):
        return "ERROR: only plain arithmetic expressions are allowed."
    try:
        value = eval(expr, {"__builtins__": {}}, {})
        return str(value)
    except Exception as exc:
        return f"ERROR: {exc}"


# ---------------------------------------------------------------------------
# Schemas (structured outputs)
# ---------------------------------------------------------------------------
class Action(BaseModel):
    """Step 2: the schema-validated action the model must return.

    NOTE: every field is explicitly typed. Do NOT use `args: dict` - strict
    structured-output mode requires additionalProperties:false on every object,
    and a bare dict cannot express that (the provider returns HTTP 400).
    """
    tool: Literal["calculator", "final_answer"]
    expr: Optional[str] = Field(
        default=None, description="Arithmetic expression, when tool='calculator'.")
    text: Optional[str] = Field(
        default=None, description="The answer text, when tool='final_answer'.")


class Plan(BaseModel):
    """Step 6: an ordered list of concrete, tool-executable steps."""
    steps: list[str]


def log_event(name: str, **fields):
    """Simple trace helper for agent execution."""
    details = " | ".join(f"{k}={v}" for k, v in fields.items())
    if details:
        print(f"[{name}] {details}")
    else:
        print(f"[{name}]")


llm = ChatOpenAI(
    model="openai/gpt-4o-mini",
    temperature=0,
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY", ""),
)
structured_llm = llm.with_structured_output(Action)
planner_llm = llm.with_structured_output(Plan)


# ---------------------------------------------------------------------------
# Graph state
# ---------------------------------------------------------------------------
class State(TypedDict):
    question: str
    scratchpad: list
    action: Optional[dict]
    answer: Optional[str]
    plan: list
    past_steps: list
    steps_used: int       # Step 5: the MAX_STEPS budget counter
    replans: int          # Step 8: the MAX_REPLANS budget counter


# ---------------------------------------------------------------------------
# PART 1 — ReAct nodes
# ---------------------------------------------------------------------------
def reason(state: State) -> State:
    """Ask the model for its next move using the full scratchpad as memory."""
    observations = "\n".join(str(item) for item in state.get("scratchpad", [])) if state.get("scratchpad") else "(nothing yet)"
    log_event("reason.start", question=state["question"], scratchpad_count=len(state.get("scratchpad", [])))
    prompt = (
        "Answer the question below, one step at a time.\n"
        "Use the calculator tool for arithmetic when needed.\n"
        "If you already know the answer, return final_answer.\n\n"
        f"QUESTION: {state['question']}\n\n"
        f"OBSERVATIONS SO FAR:\n{observations}"
    )
    action = structured_llm.invoke(prompt)
    state["action"] = action.model_dump(exclude_none=True)
    state["steps_used"] = int(state.get("steps_used", 0)) + 1
    log_event("reason.decided", action=state["action"], steps_used=state["steps_used"])
    return state


def act(state: State) -> State:
    """Execute the chosen action and record the result in the scratchpad."""
    action = state.get("action") or {}
    tool = action.get("tool")
    log_event("act.start", tool=tool, action=action)

    if tool == "final_answer":
        state["answer"] = action.get("text") or "(no answer provided)"
        log_event("act.final_answer", answer=state["answer"])
        return state

    if tool == "calculator":
        expr = action.get("expr") or ""
        result = calculator(expr)
        observation = f"calculator({expr}) = {result}"
        state.setdefault("scratchpad", []).append(observation)
        log_event("act.calculator", expr=expr, result=result, observation=observation)
        return state

    state["scratchpad"] = state.get("scratchpad", [])
    state["scratchpad"].append("ERROR: unknown tool requested.")
    log_event("act.error", message="unknown tool requested", scratchpad=state["scratchpad"])
    return state


def is_done(state: State) -> str:
    """Stop once the answer exists or the step budget has been exhausted."""
    if state.get("answer"):
        return "end"
    if state.get("steps_used", 0) >= MAX_STEPS:
        state["answer"] = "(gave up - ran out of steps)"
        return "end"
    return "loop"


# ---------------------------------------------------------------------------
# PART 2 — Planning nodes
# ---------------------------------------------------------------------------
def planner(state: State) -> State:
    """Decompose the question into concrete executable steps."""
    log_event("planner.start", question=state["question"])
    prompt = (
        "Break the request into a short ordered list of single, concrete, tool-executable steps.\n"
        "Each step should be one action the agent can do with the calculator or a final answer.\n"
        "Do not include vague instructions.\n\n"
        f"QUESTION: {state['question']}"
    )
    plan = planner_llm.invoke(prompt)
    state["plan"] = plan.steps
    state["past_steps"] = []
    state["replans"] = 0
    log_event("planner.finished", plan=state["plan"])
    return state


def executor(state: State) -> State:
    """Run the next plan step using the same reason/act mechanism as the base ReAct loop."""
    plan = state.get("plan") or []
    log_event("executor.start", remaining_plan=plan)
    if not plan:
        state["answer"] = "No remaining plan steps."
        log_event("executor.empty_plan", answer=state["answer"])
        return state

    step = plan[0]
    log_event("executor.step", step=step)
    prompt = (
        "You are executing the current plan step. Use the scratchpad and calculator as needed.\n"
        "If the step is complete, return final_answer with the computed result.\n\n"
        f"QUESTION: {state['question']}\n\n"
        f"CURRENT STEP: {step}\n\n"
        f"SCRATCHPAD:\n{chr(10).join(str(item) for item in state.get('scratchpad', [])) or '(nothing yet)'}"
    )
    action = structured_llm.invoke(prompt)
    state["action"] = action.model_dump(exclude_none=True)
    log_event("executor.decided", action=state["action"], step=step)

    tool = state["action"].get("tool")
    if tool == "final_answer":
        state["answer"] = state["action"].get("text") or "(no answer provided)"
        state["past_steps"].append((step, state["answer"]))
        log_event("executor.final_answer", step=step, answer=state["answer"]) 
        return state

    if tool == "calculator":
        expr = state["action"].get("expr") or ""
        result = calculator(expr)
        observation = f"calculator({expr}) = {result}"
        state.setdefault("scratchpad", []).append(observation)
        state["past_steps"].append((step, observation))
        state["plan"] = plan[1:]
        log_event("executor.calculator", step=step, expr=expr, result=result, remaining_plan=state["plan"])
        return state

    state["past_steps"].append((step, "ERROR: unknown tool requested."))
    state["plan"] = plan[1:]
    log_event("executor.error", step=step, message="unknown tool requested", past_steps=state["past_steps"])
    return state


def replan(state: State) -> State:
    """Decide whether the current evidence is enough to answer or if a revised plan is needed."""
    log_event("replan.start", past_steps=state.get("past_steps", []), scratchpad=state.get("scratchpad", []))
    if state.get("answer"):
        log_event("replan.answer_exists", answer=state["answer"])
        return state

    state["replans"] = int(state.get("replans", 0)) + 1
    log_event("replan.count", replans=state["replans"], max_replans=MAX_REPLANS)
    if state["replans"] >= MAX_REPLANS:
        state["answer"] = "(gave up - ran out of replans)"
        log_event("replan.timeout", answer=state["answer"])
        return state

    prompt = (
        "Review the question, the scratchpad, and the steps already completed.\n"
        "If the evidence is sufficient to answer, produce a final answer.\n"
        "Otherwise, produce a short revised plan of concrete remaining steps.\n\n"
        f"QUESTION: {state['question']}\n\n"
        f"PAST STEPS:\n{state.get('past_steps', [])}\n\n"
        f"SCRATCHPAD:\n{chr(10).join(str(item) for item in state.get('scratchpad', [])) or '(nothing yet)'}"
    )
    action = structured_llm.invoke(prompt)
    log_event("replan.model_decision", action=action.model_dump(exclude_none=True))
    if action.tool == "final_answer":
        state["answer"] = action.text or "(no answer provided)"
        log_event("replan.final_answer", answer=state["answer"])
        return state

    revised_plan = planner_llm.invoke(
        "Return only the remaining concrete steps as a short ordered list.\n\n"
        f"QUESTION: {state['question']}\n\n"
        f"REVIEW:\n{prompt}"
    )
    state["plan"] = revised_plan.steps
    log_event("replan.revised_plan", plan=state["plan"])
    return state


def replan_done(state: State) -> str:
    """Stop planning if an answer exists; otherwise continue the loop."""
    return "end" if state.get("answer") else "loop"


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------
def build_react_graph():
    """Part 1 graph: reason -> act -> (loop|END)."""
    g = StateGraph(State)
    g.add_node("reason", reason)
    g.add_node("act", act)
    g.set_entry_point("reason")
    g.add_edge("reason", "act")
    g.add_conditional_edges("act", is_done, {"end": END, "loop": "reason"})
    return g.compile()


def build_plan_execute_graph():
    """Part 2 graph: planner -> executor -> replan -> (loop|END)."""
    g = StateGraph(State)
    g.add_node("planner", planner)
    g.add_node("executor", executor)
    g.add_node("replan", replan)
    g.set_entry_point("planner")
    g.add_edge("planner", "executor")
    g.add_edge("executor", "replan")
    g.add_conditional_edges("replan", replan_done, {"end": END, "loop": "executor"})
    return g.compile()


if __name__ == "__main__":
    # ---------------------------------------------------------------------
    # SETUP GATE - run this file as-is before you write any code.
    # It checks your environment. It does NOT run an agent yet, because
    # the TODOs below are still empty.
    # ---------------------------------------------------------------------
    # import os

    # print("Module 3 setup check")
    # print("-" * 40)

    # ok = True
    # try:
    #     import langgraph
    #     print("  [ok]   langgraph imported")
    # except Exception as e:
    #     ok = False
    #     print(f"  [FAIL] langgraph: {e}")

    # try:
    #     from langchain_openai import ChatOpenAI  # noqa: F401
    #     print("  [ok]   langchain_openai imported")
    # except Exception as e:
    #     ok = False
    #     print(f"  [FAIL] langchain_openai: {e}")

    # if os.environ.get("OPENROUTER_API_KEY"):
    #     print("  [ok]   OPENROUTER_API_KEY found")
    # else:
    #     ok = False
    #     print("  [FAIL] OPENROUTER_API_KEY missing - check your .env file")

    # print("-" * 40)
    # if ok:
    #     print("READY")
    #     print("  1. read M3-Lab-Brief.md      (what you're building, and why)")
    #     print("  2. then M3-Lab-Worksheet.md  (Step 1 onwards)")
    # else:
    #     print("NOT READY - fix the [FAIL] lines above, then run this again.")

    # Once you have finished Part 2, delete everything above and use this:
    #
    q = ("A team has 3 sprints of 12, 19, and 8 story points. "
         "What's the average per sprint, and is it above 12?")
    app = build_plan_execute_graph()
    result = app.invoke({
        "question": q, "scratchpad": [], "action": None, "answer": None,
        "plan": [], "past_steps": [], "steps_used": 0, "replans": 0,
    })
    print("ANSWER:", result.get("answer"))
    
    # Step 9: visualize ->  print(app.get_graph().draw_mermaid())
