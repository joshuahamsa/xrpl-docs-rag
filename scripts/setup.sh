#!/usr/bin/env bash
# One-shot setup for xrpl-docs-rag on a new machine:
# venv + install, index build, and a global Claude Code skill pointing here.
#
# Usage: scripts/setup.sh [--no-ingest] [--no-skill]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INGEST=1
SKILL=1
for arg in "$@"; do
  case "$arg" in
    --no-ingest) INGEST=0 ;;
    --no-skill) SKILL=0 ;;
    *) echo "Unknown option: $arg" >&2; exit 1 ;;
  esac
done

cd "$REPO_ROOT"

if [ ! -x .venv/bin/python ]; then
  echo "==> Creating virtualenv"
  python3 -m venv .venv
fi
echo "==> Installing package"
.venv/bin/python -m pip install --quiet --upgrade pip
.venv/bin/python -m pip install --quiet -e '.[dev]'

if [ "$INGEST" -eq 1 ]; then
  echo "==> Building index (clones/updates doc sources; this takes a while)"
  .venv/bin/xrpl-rag ingest
fi

if [ "$SKILL" -eq 1 ]; then
  SKILL_DIR="${HOME}/.claude/skills/xrpl-docs"
  echo "==> Installing global Claude Code skill at ${SKILL_DIR}"
  mkdir -p "$SKILL_DIR"
  cat > "${SKILL_DIR}/SKILL.md" <<EOF
---
name: xrpl-docs
description: Search the local XRPL documentation RAG index (xrpl.org docs, xrpl-py, xrpl.js). Use whenever answering questions about the XRP Ledger, XRPL transactions, accounts, amendments, or the xrpl-py/xrpl.js client libraries — before answering from memory.
---

# XRPL Docs RAG

A local RAG index of xrpl.org documentation plus the xrpl-py and xrpl.js client
library docs lives at \`${REPO_ROOT}\`. Always ground XRPL answers in it
instead of answering from memory.

## How to query

\`\`\`bash
cd ${REPO_ROOT} && .venv/bin/xrpl-rag search "<question>"
\`\`\`

For a larger, LLM-ready context block (more chunks, formatted for pasting):

\`\`\`bash
cd ${REPO_ROOT} && .venv/bin/xrpl-rag context "<question>"
\`\`\`

Notes:

- The first query in a session loads the embedding model (~a few seconds);
  Hugging Face rate-limit warnings on stderr are harmless.
- Results include xrpl.org URLs — cite them in answers.
- If results look thin or stale, the index can be rebuilt with
  \`.venv/bin/xrpl-rag ingest\` (downloads/updates doc repos; slow — ask first).
- Run several differently-phrased searches for broad questions; each query
  returns only the top-ranked chunks.
EOF
fi

echo "==> Done. Test with: ${REPO_ROOT}/.venv/bin/xrpl-rag search \"How do Tickets work?\""
