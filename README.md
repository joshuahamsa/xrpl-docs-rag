# XRPL Docs RAG

Local-first retrieval for the official XRP Ledger documentation. The CLI indexes xrpl.org source docs and prints source-cited context that you can hand to a local LLM.

## Install

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
```

The first ingest downloads the local embedding model used by `sentence-transformers`.

## Build The Index

Clone or update the official XRPL docs source and build a local Chroma vector store:

```bash
.venv/bin/xrpl-rag ingest
```

Use an existing checkout without network updates:

```bash
.venv/bin/xrpl-rag ingest --docs-path /path/to/xrpl-dev-portal --no-update
```

Defaults:

- Docs checkout: `.cache/xrpl-dev-portal`
- Vector DB: `.rag/chroma`
- Collection: `xrpl_docs`
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2`

## Search

```bash
.venv/bin/xrpl-rag search "How do Tickets work?"
```

This prints ranked XRPL docs chunks with headings, xrpl.org URLs, source files, and scores.

## Create Local LLM Context

```bash
.venv/bin/xrpl-rag context "How do I submit a Payment transaction?"
```

Paste the output into Ollama, LM Studio, llama.cpp, Open WebUI, Jan, or any other local LLM chat. The command does not call a hosted LLM or generate answers itself.

## Map A Codebase

Create JSONL and Markdown records for a C/C++ source tree:

```bash
.venv/bin/xrpl-rag map-code /path/to/xrpld --out .rag/code-map --format both
```

The mapper writes `.rag/code-map/records.jsonl` plus Markdown review files under `.rag/code-map/markdown`. The first version uses deterministic C/C++ parsing and does not call hosted LLMs.

Progress updates are printed by default. For large codebases, lower sustained CPU usage with a small per-file throttle:

```bash
.venv/bin/xrpl-rag map-code /path/to/xrpld --out .rag/code-map --format both --progress-every 100 --throttle-ms 5
```

## Environment Overrides

```bash
export XRPL_RAG_DOCS_PATH=/path/to/xrpl-dev-portal
export XRPL_RAG_DB_PATH=/path/to/chroma
export XRPL_RAG_COLLECTION=xrpl_docs
export XRPL_RAG_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

## Development

```bash
.venv/bin/python -m pytest -v
.venv/bin/python -m xrpl_rag.cli --help
```
