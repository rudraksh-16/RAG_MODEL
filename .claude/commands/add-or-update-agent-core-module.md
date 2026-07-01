---
name: add-or-update-agent-core-module
description: Workflow command scaffold for add-or-update-agent-core-module in RAG_MODEL.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /add-or-update-agent-core-module

Use this workflow when working on **add-or-update-agent-core-module** in `RAG_MODEL`.

## Goal

Add or update core agent modules, such as tool classes, argument schemas, constants, or the main agent logic.

## Common Files

- `src/llm/agent_core/agent.py`
- `src/llm/agent_core/tool.py`
- `src/llm/agent_core/args_schema.py`
- `src/llm/agent_core/constant.py`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Create or update files in src/llm/agent_core/ (e.g., agent.py, tool.py, args_schema.py, constant.py)
- Commit with a message referencing agent core, tool, or schema

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.