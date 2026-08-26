# XRPL Docs RAG Design

## Goal

Build a local-first RAG pipeline that indexes the official XRPL documentation and emits source-cited context blocks suitable for any local LLM.

## Source

The pipeline ingests from `https://github.com/XRPLF/xrpl-dev-portal`, the public source repository for xrpl.org documentation. The default local checkout path is `.cache/xrpl-dev-portal`.

The ingester supports two modes:

- `clone/update`: clone the repository if missing, otherwise fetch and fast-forward the existing checkout.
- `local path`: ingest from a caller-provided docs checkout without network access.

## Interface

The first deliverable is a Python CLI with these commands:

```bash
xrpl-rag ingest
xrpl-rag search "How do Tickets work?"
xrpl-rag context "How do I submit a payment transaction?"
```

`ingest` builds or refreshes the local vector store.

`search` prints ranked matching chunks with title, heading path, source file, xrpl.org URL, and score.

`context` prints a prompt-ready block for a local LLM:

```text
Question: ...

Relevant XRPL docs:
[1] Page title
Heading: ...
URL: ...
Excerpt: ...
```

The CLI must not call a hosted LLM. It may use local embedding models downloaded by `sentence-transformers`.

## Architecture

The package is split into focused modules:

- `config`: filesystem defaults and environment overrides.
- `docs_source`: clone, update, or validate a local docs repository.
- `parser`: read Markdown/MDX files, extract frontmatter, title, heading hierarchy, text, and canonical docs URL metadata.
- `chunker`: split parsed pages into heading-aware chunks with bounded size and overlap.
- `embeddings`: provide local sentence-transformer embeddings behind a small interface.
- `store`: persist chunks and vectors in a local Chroma database.
- `retrieval`: query the vector store and return ranked document chunks.
- `formatting`: render search and LLM context output.
- `cli`: Typer command wiring.

## Chunking

Chunks should preserve semantic locality:

- Prefer section boundaries from Markdown headings.
- Include page title and heading path in the embedded text.
- Keep chunk text around 700-1,000 words when possible.
- Use modest overlap for long sections so definitions are not separated from examples.
- Preserve code blocks as text because XRPL docs include request and transaction examples.

## Metadata

Every stored chunk includes:

- `chunk_id`: stable hash of source path, heading path, and chunk index.
- `source_path`: repository-relative path.
- `title`: page title from frontmatter, H1, or file name fallback.
- `heading_path`: joined Markdown headings for the chunk.
- `url`: best-effort xrpl.org docs URL derived from source path.
- `text`: raw chunk text.

Stable IDs allow re-ingestion to update existing records without duplicating chunks.

## Configuration

Default paths:

- Docs repo: `.cache/xrpl-dev-portal`
- Vector DB: `.rag/chroma`
- Collection: `xrpl_docs`
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2`

Environment overrides:

- `XRPL_RAG_DOCS_PATH`
- `XRPL_RAG_DB_PATH`
- `XRPL_RAG_COLLECTION`
- `XRPL_RAG_EMBEDDING_MODEL`

## Error Handling

The CLI fails with actionable messages when:

- `git` is unavailable for clone/update mode.
- The docs path does not exist.
- No Markdown/MDX documentation files are found.
- The vector store has not been built before `search` or `context`.

## Testing

Automated tests cover:

- Markdown parsing with frontmatter, headings, prose, and code blocks.
- Heading-aware chunk creation and stable chunk IDs.
- URL derivation from common XRPL docs paths.
- Context formatting for local LLM handoff.

Tests should use small fixtures and avoid network calls, hosted LLMs, and external XRPL repo state.

## Out of Scope

This version does not include:

- A web UI.
- Hosted LLM calls.
- Automatic answer generation.
- Incremental git diff indexing.
- Multi-source indexing beyond the official XRPL docs repository.
