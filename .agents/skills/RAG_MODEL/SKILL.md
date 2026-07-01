```markdown
# RAG_MODEL Development Patterns

> Auto-generated skill from repository analysis

## Overview

This skill teaches you the core development patterns, coding conventions, and workflows used in the `RAG_MODEL` Python codebase. The repository implements Retrieval-Augmented Generation (RAG) logic, with modular components for retrieval, agent logic, and pipeline orchestration. You'll learn how to add new retrieval or agent modules, update the pipeline, and follow the project's conventions for clean, maintainable code.

---

## Coding Conventions

**File Naming**
- Use `snake_case` for all file and module names.
  - Example: `rerank.py`, `args_schema.py`

**Import Style**
- Use **relative imports** within modules.
  - Example:
    ```python
    from .tool import Tool
    from ..retrieval.rerank import rerank_documents
    ```

**Export Style**
- Use **named exports** (explicitly define what is exported).
  - Example:
    ```python
    def rerank_documents(...):
        ...
    __all__ = ["rerank_documents"]
    ```

**Commit Messages**
- Use prefixes like `feat`, `fix`, `chore`, `chores` (typos like `chroes` exist but should be avoided).
- Keep commit messages concise (~35 characters on average).
  - Example: `feat: add rerank module for retrieval`

---

## Workflows

### Add or Update Retrieval Component
**Trigger:** When you want to implement or improve retrieval logic (e.g., reranking, search) in the RAG system.  
**Command:** `/add-retrieval-component`

1. Create or update a file in `src/llm/rag/retrieval/` (e.g., `rerank.py`, `search.py`).
2. Optionally, update related files if needed (e.g., both `rerank.py` and `search.py`).
3. Commit your changes with a message referencing "retrieval", "rerank", or "search".

**Example:**
```python
# src/llm/rag/retrieval/rerank.py
def rerank_documents(docs, query):
    # Implement reranking logic here
    return sorted(docs, key=lambda d: score(d, query), reverse=True)
```
**Commit:** `feat: add rerank_documents to retrieval`

---

### Add or Update Agent Core Module
**Trigger:** When you want to introduce or modify foundational agent logic or configuration.  
**Command:** `/add-agent-core`

1. Create or update files in `src/llm/agent_core/` (e.g., `agent.py`, `tool.py`, `args_schema.py`, `constant.py`).
2. Commit your changes with a message referencing "agent core", "tool", or "schema".

**Example:**
```python
# src/llm/agent_core/tool.py
class Tool:
    def __init__(self, name):
        self.name = name
```
**Commit:** `feat: add Tool class to agent_core`

---

### Add or Update RAG Agent Module
**Trigger:** When you want to implement or modify the RAG agent's behavior or prompt engineering.  
**Command:** `/add-rag-agent-module`

1. Create or update files in `src/llm/rag/rag_agent/` (e.g., `agent.py`, `prompt.py`, `tools/make_retrieval.py`).
2. Optionally, update related constants or generation files.
3. Commit your changes with a message referencing "rag agent" or "prompt".

**Example:**
```python
# src/llm/rag/rag_agent/prompt.py
def build_prompt(context, question):
    return f"Context: {context}\nQuestion: {question}\nAnswer:"
```
**Commit:** `feat: add prompt builder for rag agent`

---

### Pipeline Refactor or Enhancement
**Trigger:** When you want to improve or fix the main RAG pipeline logic.  
**Command:** `/update-pipeline`

1. Create or update `src/llm/rag/pipeline.py` and/or `src/llm/rag/pipline.py` (note: fix any typos in file names if found).
2. Commit your changes with a message referencing "pipeline".

**Example:**
```python
# src/llm/rag/pipeline.py
def run_pipeline(input_data):
    # Main RAG pipeline logic
    ...
```
**Commit:** `fix: correct typo in pipeline module`

---

## Testing Patterns

- **Test Framework:** Unknown (not explicitly detected).
- **Test File Pattern:** Test files use the pattern `*.test.*` (e.g., `retrieval.test.py`).
- **Best Practice:** Place tests alongside modules or in a dedicated `tests/` directory. Use descriptive test function names.

**Example:**
```python
# src/llm/rag/retrieval/rerank.test.py
def test_rerank_documents():
    docs = [...]
    query = "example"
    result = rerank_documents(docs, query)
    assert result[0] == expected_doc
```

---

## Commands

| Command                   | Purpose                                                    |
|---------------------------|------------------------------------------------------------|
| /add-retrieval-component  | Add or update retrieval, rerank, or search functionality   |
| /add-agent-core           | Add or update core agent modules or configuration          |
| /add-rag-agent-module     | Add or update RAG agent logic or prompt engineering        |
| /update-pipeline          | Refactor or enhance the main RAG pipeline                  |
```
