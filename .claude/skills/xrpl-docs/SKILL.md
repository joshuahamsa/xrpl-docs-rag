---
name: xrpl-docs
description: Search the local XRPL documentation RAG index (xrpl.org docs, the xrpl-py/xrpl.js/xrpl4j/xrpl-go client libraries, XLS standards, Clio, Xahau/Hooks, and the Xaman, Joey, GemWallet, and Ledger wallet developer docs). Use whenever answering questions about the XRP Ledger, XRPL transactions, accounts, amendments, XLS proposals, client libraries, Xahau Hooks, or XRPL wallet integrations — before answering from memory.
---

# XRPL Docs RAG

This repo contains a local RAG index of xrpl.org documentation plus the xrpl-py
and xrpl.js client library docs and the Xaman and Joey Wallet developer docs. Always ground XRPL answers in it instead of
answering from memory.

## How to query

Run from the repo root (`/Volumes/NVME/Dev/RAG`):

```bash
.venv/bin/xrpl-rag search "<question>"
```

For a larger, LLM-ready context block (more chunks, formatted for pasting):

```bash
.venv/bin/xrpl-rag context "<question>"
```

Notes:

- The first query in a session loads the embedding model (~a few seconds);
  Hugging Face rate-limit warnings on stderr are harmless.
- Results include xrpl.org URLs — cite them in answers.
- If results look thin or stale, the index can be rebuilt with
  `.venv/bin/xrpl-rag ingest` (downloads/updates doc repos; slow — ask first).
- Run several differently-phrased searches for broad questions; each query
  returns only the top-ranked chunks.
