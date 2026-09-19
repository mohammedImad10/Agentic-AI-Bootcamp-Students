"""check_prd.py — the referee for the prd-writer skill.

Deterministic checks do not belong in the model. Counting required sections
and banning vague phrasing is not a reasoning task. Every check moved OUT of
the prompt and INTO a script is a check that can no longer be argued with,
forgotten, or hallucinated as passed.

Reads the draft on stdin, prints a verdict plus the text.
"""

import re
import sys

REQUIRED = [
    "## Overview",
    "## Goals & Success Metrics",
    "## User Stories",
    "## Scope",
    "## Business Requirements",
    "## Technical Requirements",
    "## Risks & Assumptions",
    "## Rollout Plan",
]

REQUIRED_SUBHEADINGS = [
    "### Out of Scope",
    "### Non-Functional Requirements",
]

VAGUE_NFR_PHRASES = [
    "should be fast",
    "should be secure",
    "highly scalable",
    "very performant",
    "as needed",
    "good ux",
    "improve ux",
]

BANNED = [
    "in today's fast-paced",
    "it is important to note",
    "in conclusion",
    "delve into",
    "landscape of",
]


def check(text: str) -> list[str]:
    problems = []
    lowered = text.lower()

    missing = [h for h in REQUIRED if h not in text]
    if missing:
        problems.append("MISSING SECTIONS: " + ", ".join(missing))

    positions = [text.find(h) for h in REQUIRED if h in text]
    if positions != sorted(positions):
        problems.append("SECTIONS OUT OF ORDER: " + " -> ".join(REQUIRED))

    missing_sub = [h for h in REQUIRED_SUBHEADINGS if h not in text]
    if missing_sub:
        problems.append("MISSING SUBSECTIONS: " + ", ".join(missing_sub))

    if not re.search(r"BR-\d+", text):
        problems.append("NO BUSINESS REQUIREMENTS: expected at least one BR-1, BR-2, ...")

    if not re.search(r"TR-\d+", text):
        problems.append("NO TECHNICAL REQUIREMENTS: expected at least one TR-1, TR-2, ...")

    for phrase in VAGUE_NFR_PHRASES:
        if phrase in lowered:
            problems.append(f"VAGUE NFR: '{phrase}' — replace with a concrete target/number.")

    for phrase in BANNED:
        if phrase in lowered:
            problems.append(f"BANNED PHRASE: '{phrase}' — rewrite that sentence.")

    if "## Technical Requirements" in text:
        tr_block = text.split("## Technical Requirements", 1)[1]
        tr_block = tr_block.split("## Risks & Assumptions", 1)[0]
        for nfr in ["Scalability", "Performance", "Security", "Reliability"]:
            if nfr not in tr_block:
                problems.append(f"MISSING NFR: no '{nfr}' target found under Non-Functional Requirements.")

    return problems


def main() -> None:
    text = sys.stdin.read()
    problems = check(text)
    if problems:
        print("FAIL — fix these and resubmit:")
        for p in problems:
            print(f"  - {p}")
    else:
        print("PASS — all required sections, requirement IDs, and NFR targets present.")
    print("\n--- draft as received ---")
    print(text)


if __name__ == "__main__":
    main()
