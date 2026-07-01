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
