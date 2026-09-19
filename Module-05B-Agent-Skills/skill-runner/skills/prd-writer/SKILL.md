---
name: prd-writer
description: Draft a professional, scalable Product Requirements Document (PRD) for a feature, covering both business (problem, goals, users, success metrics) and technical (architecture, data, APIs, non-functional requirements) sections. Use when the user asks for a "PRD", "product requirements doc", "feature spec", "requirements document" or "write up this feature for engineering and stakeholders".
---

# Skill: PRD Writer

The house format for a feature-level Product Requirements Document. One
document, two audiences: it must let a stakeholder decide "should we build
this" and let an engineer decide "how do we build this so it scales."

## When to use this

Fires on: "PRD", "product requirements document", "feature spec", "write
requirements for X", "spec out this feature", "document this feature for
engineering and product".

Does **not** fire on: a quick brief or exec summary (use `jhf-brief` instead),
pure code implementation, or a bug report. If the user just wants an
explanation of a concept, answer normally.

## Steps

1. Call `read_resource("resources/prd-template.md")` to get the house
   skeleton. Do not invent your own section order.
2. Gather the missing facts before writing. If the user has not told you the
   following, ask (or state the assumption explicitly and flag it
   `[assumption]`):
   - Who is the user/persona and what problem are they hitting today
   - The business goal and how success is measured (a number, not a vibe)
   - Expected scale (users, requests/sec, data volume) — this drives every
     technical decision below
   - Any hard constraints (compliance, existing stack, deadline)
3. Draft the document section by section. Rules that are not negotiable:
   - **Overview** is 2-3 sentences: the problem, the user, the outcome.
   - **Goals & Success Metrics** are measurable (e.g. "reduce checkout time
     from 45s to <15s"), never "improve UX."
   - **User Stories** follow `As a <persona>, I want <capability>, so that
     <benefit>` — at least one per primary flow.
   - **Scope** has an explicit **Out of Scope** list. A PRD that only says
     what's in scope is not done.
   - **Business Requirements** are numbered (BR-1, BR-2, ...) and each is
     independently testable.
   - **Technical Requirements** are numbered (TR-1, TR-2, ...) and must cover,
     at minimum: system/architecture overview, data model, API contract, and
     a **Non-Functional Requirements** subsection with explicit targets for
     scalability (load it must handle), performance (latency/throughput),
     security (authn/authz, data handling), and reliability (availability,
     failure modes). Vague NFRs ("should be fast", "should be secure") are a
     failure — every NFR needs a number or a concrete control.
   - **Risks & Assumptions** lists real risks with a mitigation each, not
     hedging language.
   - **Rollout Plan** has phases/milestones, not just "ship it."
   - Every requirement (BR-/TR-) must map to at least one Goal in Success
     Metrics. If it doesn't trace back, cut it or justify it.
4. Call `run_script("check_prd.py", <your draft>)`. The script enforces
   required sections, ID numbering, and bans vague NFR phrasing. It is the
   referee, not you.
5. If the script reports a problem, fix the draft and run it again.
6. Call `save_output("prd-<feature-slug>.md", <final text>)`.
7. Show the finished PRD to the user, and call out any `[assumption]` or
   `[NEEDS CLARIFICATION]` markers so they know what to confirm.

## House style

- Write for two readers at once: a PM skimming for the decision, and an
  engineer looking for the constraint that changes their design.
- Numbers beat adjectives everywhere — "handles 10k concurrent users" beats
  "highly scalable."
- No "in today's fast-paced world," no "it is important to note," no filler.
- If a fact is unverified, mark it `[assumption]` rather than dropping it or
  inventing a number. A PRD that quietly guesses is worse than one that says
  so.
