# XRPL Docs RAG

Local-first retrieval for XRP Ledger documentation. The CLI indexes xrpl.org source
docs plus the XRPL Python and JavaScript library docs, then prints source-cited
context that you can hand to a local LLM.

## Install

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
```

The first ingest downloads the local embedding model used by `sentence-transformers`.

## Build The Index

Clone or update the default XRPL documentation sources and build a local Chroma
vector store:

```bash
.venv/bin/xrpl-rag ingest
```

Default sources:

- xrpl.org docs: `https://github.com/XRPLF/xrpl-dev-portal.git`
- xrpl-py docs and package docstrings: `https://github.com/XRPLF/xrpl-py.git`
- xrpl.js docs: `https://github.com/XRPLF/xrpl.js.git`

Use an existing xrpl.org docs checkout without network updates:

```bash
.venv/bin/xrpl-rag ingest --docs-path /path/to/xrpl-dev-portal --no-update
```

Passing `--docs-path` keeps the legacy single-source behavior and indexes only that
checkout.

Defaults:

- xrpl.org docs checkout: `.cache/xrpl-dev-portal`
- xrpl-py checkout: `.cache/xrpl-py`
- xrpl.js checkout: `.cache/xrpl.js`
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

`XRPL_RAG_DOCS_PATH` overrides the xrpl.org docs checkout path. The library
checkouts default to `.cache/xrpl-py` and `.cache/xrpl.js`.

## Development

```bash
.venv/bin/python -m pytest -v
.venv/bin/python -m xrpl_rag.cli --help
```

## One-Shot Machine Setup (Claude Code integration)

On a new machine (e.g. a development server):

```bash
git clone https://github.com/joshuahamsa/xrpl-docs-rag.git && cd xrpl-docs-rag
scripts/setup.sh
```

This creates the venv, installs the package, builds the index, and installs a
global Claude Code skill at `~/.claude/skills/xrpl-docs` pointing at this
checkout, so any Claude Code session on the machine can query the index.
Flags: `--no-ingest` skips the index build, `--no-skill` skips the skill install.
