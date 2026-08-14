# Module 2 Phase 1 Mini-Project

## Setup and run

From the repository root:

```bash
./.venv/bin/python Module-02/starter-code/study_guide_langgraph_starter.py "Model Context Protocol"
./.venv/bin/python Module-02/starter-code/study_guide_crewai_starter.py "Model Context Protocol"
```

You can replace the topic with any other concept you want to test.

## Topic tested

- Model Context Protocol

## Short observations

- LangGraph made the data flow explicit through typed state and named nodes and edges.
- CrewAI automated the orchestration so the tasks were easier to describe, but the hand-off was less visible.
- For this three-step pipeline, I would choose CrewAI when the workflow is simple and descriptive, and LangGraph when I need clearer control over state transitions.
