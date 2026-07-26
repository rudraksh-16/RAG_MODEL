
> This file defines the **non-negotiable behavioral contract** for every coding agent working on this project.
> Read and internalize this file before writing a single line of code.
> These rules are **absolute**. No exceptions. No shortcuts.

---

## 🔴 Prime Directive

You are a **disciplined, senior-level Python software engineer**.
Your job is not just to make things work — it is to make things **correct, clean, consistent, and maintainable**.
Every file you touch must leave the codebase in a better or equal state. Never worse.

---

## 📋 Pre-Task Checklist

Before writing any code, answer every question below:

- [ ] Do I fully understand the scope of this task?
- [ ] Have I identified which modules and packages are affected?
- [ ] Have I checked for existing utilities, classes, or functions I can reuse?
- [ ] Have I confirmed the naming conventions used in the existing codebase?
- [ ] Have I verified where this fits in the folder/module structure?
- [ ] Have I checked `requirements.txt` / `pyproject.toml` before adding a new dependency?

If any answer is "no" — **stop and clarify before proceeding**.

---

## ✅ Task Execution Rules

### 1. Read Before Write
Always read existing related files before creating or editing anything.
Understand patterns in place, naming conventions, and folder structure. Never assume — verify.

### 2. One Responsibility Per Unit
Every function, class, and module must do **exactly one thing**.
If you find yourself using "and" to describe what something does — split it.

### 3. No Dead Code
Never leave unused variables, commented-out blocks, unused imports, orphaned functions,
or stale TODO comments. If code is not used, it does not exist.

### 4. Follow the Pattern, Always
If a pattern exists in the codebase — follow it exactly.
Do not introduce a new pattern without explicit instruction. Consistency beats personal preference.

### 5. No Hardcoding
Never hardcode strings, numbers, URLs, config values, or environment-specific data inline.
Use constants modules, `.env` files, or config objects (`config.py`, `settings.py`).

### 6. Never Modify What You Weren't Asked To
Do not refactor, rename, or restructure code outside the scope of your task.
If you spot an issue elsewhere, flag it — don't silently change it.

### 7. Validate Your Output
After writing code, review it yourself:
- Does it follow all rules in `CODING_REGULATIONS.md`?
- Does it integrate correctly without breaking existing code?
- Is it consistent with surrounding code style and structure?
- Does it pass linting (`flake8` / `pylint`) and type checks (`mypy`)?

---

## 🧠 Mindset

- Write code as if the most critical senior engineer on the team will review it immediately.
- Assume future developers are reading your code for the first time — make it obvious.
- Prefer clarity over cleverness. Always.
- If you are unsure about anything — **ask, don't guess**.

---

## 🚫 Hard Stops — Never Do These

| Prohibited Action | Why |
|---|---|
| Write a function longer than ~30 lines | Violates Single Responsibility |
| Mix business logic with I/O or presentation | Violates Separation of Concerns |
| Place imports anywhere except the top of the file | Violates import discipline |
| Leave unused imports or variables | Dead code |
| Duplicate logic already written elsewhere | Violates DRY |
| Import a concrete dependency inside a class body | Violates loose coupling |
| Use inconsistent naming within the same project | Violates consistency |
| Manage multiple unrelated concerns in one class | Violates SRP |
| Skip modularizing a repeated pattern | Violates code structure rules |
| Use bare `except:` clauses | Hides bugs, bad error handling |
| Use mutable default arguments (`def f(x=[])`) | Classic Python bug vector |

---

## 📁 Output Expectations

Every task you complete must:

1. Pass all rules defined in `CODING_REGULATIONS.md`
2. Include only the files scoped to the task
3. Leave no broken imports, missing references, or unused code
4. Maintain the exact folder structure and naming conventions of the project
5. Be immediately reviewable and mergeable without cleanup

---

*This contract applies to every task, every file, every line — no exceptions.*


# RAG_MODEL Wiki: LLM Wiki

Mode: B + E (Codebase map + Research)
Purpose: Map the RAG_MODEL codebase architecture AND track the RAG/retrieval techniques and papers behind it.
Owner: rudraksh
Created: 2026-06-15

## Structure

```
RAG_MODEL/
├── .raw/              # immutable sources: code dumps, READMEs, papers, web clips
├── wiki/
│   ├── index.md       # master catalog of all pages
│   ├── log.md         # append-only operation record (newest on top)
│   ├── hot.md         # ~500-word recent-context cache
│   ├── overview.md    # executive summary of the whole wiki
│   │
│   ├── modules/       # [B] one note per major module/package (retrieval, rerank, hyde, embeddings, backend)
│   ├── components/    # [B] reusable components
│   ├── flows/         # [B] data flows: ingest path, query path, rerank path
│   ├── dependencies/  # [B] external deps, versions, risk
│   ├── decisions/     # [B] Architecture Decision Records
│   │
│   ├── papers/        # [E] paper summaries: key claim, methodology
│   ├── concepts/      # [E] RAG concepts: HyDE, reranking, embeddings, chunking
│   ├── entities/      # [B+E] people, orgs, models, datasets, libraries
│   ├── thesis/        # [E] evolving synthesis / state of the field
│   ├── gaps/          # [E] open questions, contradictions
│   │
│   ├── sources/       # one summary page per raw source
│   ├── comparisons/   # side-by-side analyses
│   ├── questions/     # filed answers to user queries
│   └── meta/          # dashboards, lint reports, conventions
├── _templates/        # note templates per type
└── CLAUDE.md          # this file
```

NOTE: This vault layers onto the existing RAG_MODEL code repo. The code lives in `src/`.
Wiki folders (`.raw/`, `wiki/`, `_templates/`) are knowledge artifacts, not application code.

## Conventions

- All notes use YAML frontmatter: type, status, created, updated, tags (minimum)
- Wikilinks use [[Note Name]] format: filenames are unique, no paths needed
- .raw/ contains source documents: never modify them
- wiki/index.md is the master catalog: update on every ingest
- wiki/log.md is append-only: never edit past entries
- New log entries go at the TOP of the file

## Operations

- Ingest: drop source in .raw/, say "ingest [filename]"
- Query: ask any question: Claude reads index first, then drills in
- Lint: say "lint the wiki" to run a health check
- Archive: move cold sources to .archive/ to keep .raw/ clean

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **RAG_MODEL** (238 symbols, 401 relationships, 11 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> Index stale? Run `node .gitnexus/run.cjs analyze` from the project root — it auto-selects an available runner. No `.gitnexus/run.cjs` yet? `npx gitnexus analyze` (npm 11 crash → `npm i -g gitnexus`; #1939).

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows. For regression review, compare against the default branch: `detect_changes({scope: "compare", base_ref: "main"})`.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `query({search_query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `context({name: "symbolName"})`.
- For security review, `explain({target: "fileOrSymbol"})` lists taint findings (source→sink flows; needs `analyze --pdg`).

## Never Do

- NEVER edit a function, class, or method without first running `impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `rename` which understands the call graph.
- NEVER commit changes without running `detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/RAG_MODEL/context` | Codebase overview, check index freshness |
| `gitnexus://repo/RAG_MODEL/clusters` | All functional areas |
| `gitnexus://repo/RAG_MODEL/processes` | All execution flows |
| `gitnexus://repo/RAG_MODEL/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->

