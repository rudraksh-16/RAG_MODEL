---
name: add-or-update-retrieval-component
description: Workflow command scaffold for add-or-update-retrieval-component in RAG_MODEL.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /add-or-update-retrieval-component

Use this workflow when working on **add-or-update-retrieval-component** in `RAG_MODEL`.

## Goal

Add or update retrieval-related functionality, such as rerankers or search modules, to the RAG pipeline.

## Common Files

- `src/llm/rag/retrieval/rerank.py`
- `src/llm/rag/retrieval/search.py`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Create or update a file in src/llm/rag/retrieval/ (e.g., rerank.py, search.py)
- Optionally, update related files (e.g., both rerank.py and search.py together)
- Commit with a message referencing retrieval, rerank, or search

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.