# XRPL Docs RAG

Local RAG pipeline over xrpl.org docs and the xrpl-py / xrpl.js client libraries.

## Answering XRPL questions

Use the `xrpl-docs` skill (`.claude/skills/xrpl-docs/`): query the local index
with `.venv/bin/xrpl-rag search "<question>"` before answering any XRP Ledger
question from memory, and cite the xrpl.org URLs it returns.

## Development

- Install: `python3 -m venv .venv && .venv/bin/python -m pip install -e '.[dev]'`
- Tests: `.venv/bin/python -m pytest`
- CLI entry point: `src/xrpl_rag/cli.py` (Typer app; commands: ingest, search, context, map-code)
- Vector store: Chroma at `.rag/chroma`, collection `xrpl_docs`
- Doc checkouts are cached under `.cache/`
