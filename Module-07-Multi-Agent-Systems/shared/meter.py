"""
shared/meter.py  --  a small, honest meter: what did this run cost?

Every exercise ends by printing a card like this:

    ── what that cost ────────────────────────────────────────
      agents that worked ... 3
      LLM calls ............ 4
      tokens ............... 1,512   (in 1,190 / out 322)
      money ................ $0.00037  (openai/gpt-4o-mini)
      time ................. 9.8 s

A team of agents is never free. Keep an eye on these numbers all day.
"""

from __future__ import annotations

import threading
import time

# USD per 1,000,000 tokens on OpenRouter, checked 29 Sep 2026.
PRICES = {
    "openai/gpt-4o-mini": (0.15, 0.60),
    "openai/gpt-4.1-mini": (0.40, 1.60),
}


class Meter:
    """Counts LLM calls and tokens. Safe to use from agents running in parallel."""

    def __init__(self) -> None:
        self.calls = 0
        self.tokens_in = 0
        self.tokens_out = 0
        self._lock = threading.Lock()
        self._start = time.perf_counter()

    def record(self, reply) -> None:
        """Pass it a LangChain reply (from llm.invoke) and it adds the usage."""
        usage = getattr(reply, "usage_metadata", None) or {}
        with self._lock:
            self.calls += 1
            self.tokens_in += int(usage.get("input_tokens", 0))
            self.tokens_out += int(usage.get("output_tokens", 0))

    def record_crew(self, crew_output) -> None:
        """Pass it what crew.kickoff() returned and it adds the crew's usage."""
        usage = getattr(crew_output, "token_usage", None)
        if usage is None:
            return
        with self._lock:
            self.calls += int(getattr(usage, "successful_requests", 0) or 0)
            self.tokens_in += int(getattr(usage, "prompt_tokens", 0) or 0)
            self.tokens_out += int(getattr(usage, "completion_tokens", 0) or 0)

    def seconds(self) -> float:
        return time.perf_counter() - self._start

    def dollars(self, model: str) -> float | None:
        price = PRICES.get(model)
        if price is None:
            return None
        return (self.tokens_in * price[0] + self.tokens_out * price[1]) / 1_000_000

    def card(self, *, agents: int, model: str, note: str = "") -> str:
        money = self.dollars(model)
        money_txt = f"${money:.5f}  ({model})" if money is not None else f"(no price on file for {model})"
        lines = [
            "── what that cost " + "─" * 42,
            f"  agents that worked ... {agents}",
            f"  LLM calls ............ {self.calls}",
            f"  tokens ............... {self.tokens_in + self.tokens_out:,}   "
            f"(in {self.tokens_in:,} / out {self.tokens_out:,})",
            f"  money ................ {money_txt}",
            f"  time ................. {self.seconds():.1f} s",
        ]
        if note:
            lines.append(f"  note ................. {note}")
        return "\n".join(lines)


def banner(title: str) -> str:
    bar = "═" * 64
    return f"\n{bar}\n {title}\n{bar}"


def indent(text: str, prefix: str = "   ") -> str:
    return "\n".join(prefix + line for line in str(text).strip().splitlines())
