# XRPL Docs RAG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local-first CLI that indexes official XRPL docs and emits source-cited context for a local LLM.

**Architecture:** A Python package exposes focused modules for config, docs source management, Markdown parsing, chunking, embedding, vector storage, retrieval, formatting, and Typer CLI wiring. Tests cover the behavior that can be verified without network access or model downloads.

**Tech Stack:** Python 3.10+, Typer, ChromaDB, sentence-transformers, PyYAML, pytest.

**Spec:** `docs/superpowers/specs/2026-08-26-xrpl-docs-rag-design.md`

## Global Constraints

- Do not call a hosted LLM.
- Default docs repo path: `.cache/xrpl-dev-portal`.
- Default vector DB path: `.rag/chroma`.
- Default collection: `xrpl_docs`.
- Default embedding model: `sentence-transformers/all-MiniLM-L6-v2`.
- Environment overrides: `XRPL_RAG_DOCS_PATH`, `XRPL_RAG_DB_PATH`, `XRPL_RAG_COLLECTION`, `XRPL_RAG_EMBEDDING_MODEL`.
- Tests must avoid network calls, hosted LLMs, and external XRPL repo state.

---

### Task 1: Package Skeleton and Config

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `src/xrpl_rag/__init__.py`
- Create: `src/xrpl_rag/config.py`
- Create: `tests/test_config.py`

**Interfaces:**
- Produces: `RagConfig.from_env() -> RagConfig`
- Produces: `RagConfig.resolve(base_path: Path) -> RagConfig`

- [ ] **Step 1: Write the failing tests**

```python
from pathlib import Path

from xrpl_rag.config import RagConfig


def test_config_resolves_relative_paths(tmp_path, monkeypatch):
    monkeypatch.delenv("XRPL_RAG_DOCS_PATH", raising=False)
    monkeypatch.delenv("XRPL_RAG_DB_PATH", raising=False)
    config = RagConfig.from_env().resolve(tmp_path)

    assert config.docs_path == tmp_path / ".cache" / "xrpl-dev-portal"
    assert config.db_path == tmp_path / ".rag" / "chroma"
    assert config.collection_name == "xrpl_docs"
    assert config.embedding_model == "sentence-transformers/all-MiniLM-L6-v2"


def test_config_uses_environment_overrides(tmp_path, monkeypatch):
    docs_path = tmp_path / "docs"
    db_path = tmp_path / "db"
    monkeypatch.setenv("XRPL_RAG_DOCS_PATH", str(docs_path))
    monkeypatch.setenv("XRPL_RAG_DB_PATH", str(db_path))
    monkeypatch.setenv("XRPL_RAG_COLLECTION", "custom")
    monkeypatch.setenv("XRPL_RAG_EMBEDDING_MODEL", "local-model")

    config = RagConfig.from_env().resolve(tmp_path)

    assert config.docs_path == docs_path
    assert config.db_path == db_path
    assert config.collection_name == "custom"
    assert config.embedding_model == "local-model"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL because `xrpl_rag.config` does not exist.

- [ ] **Step 3: Implement package skeleton and config**

Create `pyproject.toml` with the package metadata, dependencies, and `xrpl-rag = "xrpl_rag.cli:app"` console script. Create `RagConfig` as an immutable dataclass that reads env vars and resolves relative paths against the working directory.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_config.py -v`
Expected: PASS.

### Task 2: Markdown Parsing and URL Metadata

**Files:**
- Create: `src/xrpl_rag/parser.py`
- Create: `tests/test_parser.py`

**Interfaces:**
- Produces: `ParsedPage`
- Produces: `parse_markdown_file(path: Path, repo_root: Path) -> ParsedPage`
- Produces: `derive_docs_url(source_path: str) -> str`

- [ ] **Step 1: Write the failing parser tests**

Tests should assert frontmatter title extraction, H1 fallback, code block preservation, heading extraction, and URL derivation for `docs/concepts/accounts/index.md`.

- [ ] **Step 2: Run parser tests to verify failure**

Run: `python -m pytest tests/test_parser.py -v`
Expected: FAIL because parser code does not exist.

- [ ] **Step 3: Implement parser**

Parse YAML frontmatter when present, strip MDX import/export/component tags conservatively, preserve fenced code content, extract Markdown headings, choose title from frontmatter `title`, then H1, then file stem.

- [ ] **Step 4: Run parser tests to verify pass**

Run: `python -m pytest tests/test_parser.py -v`
Expected: PASS.

### Task 3: Heading-Aware Chunking

**Files:**
- Create: `src/xrpl_rag/chunker.py`
- Create: `tests/test_chunker.py`

**Interfaces:**
- Produces: `DocumentChunk`
- Produces: `chunk_page(page: ParsedPage, max_words: int = 900, overlap_words: int = 120) -> list[DocumentChunk]`

- [ ] **Step 1: Write failing chunker tests**

Tests should assert chunks include title and heading path, long sections split with overlap, and chunk IDs are stable across repeated calls.

- [ ] **Step 2: Run chunker tests to verify failure**

Run: `python -m pytest tests/test_chunker.py -v`
Expected: FAIL because chunker code does not exist.

- [ ] **Step 3: Implement chunker**

Group prose under headings, split oversized groups by word count, prepend title and heading metadata to embedded text, and compute stable SHA-256 chunk IDs from source path, heading path, chunk index, and text.

- [ ] **Step 4: Run chunker tests to verify pass**

Run: `python -m pytest tests/test_chunker.py -v`
Expected: PASS.

### Task 4: Formatting for Search and LLM Context

**Files:**
- Create: `src/xrpl_rag/formatting.py`
- Create: `tests/test_formatting.py`

**Interfaces:**
- Produces: `SearchResult`
- Produces: `format_search_results(results: Sequence[SearchResult]) -> str`
- Produces: `format_context(question: str, results: Sequence[SearchResult]) -> str`

- [ ] **Step 1: Write failing formatting tests**

Tests should assert stable source numbering, URL inclusion, score inclusion for search output, and prompt-ready context output.

- [ ] **Step 2: Run formatting tests to verify failure**

Run: `python -m pytest tests/test_formatting.py -v`
Expected: FAIL because formatting code does not exist.

- [ ] **Step 3: Implement formatting**

Render concise CLI text with title, heading, URL, score, and excerpt. Render context text without scores so it can be pasted directly into a local LLM.

- [ ] **Step 4: Run formatting tests to verify pass**

Run: `python -m pytest tests/test_formatting.py -v`
Expected: PASS.

### Task 5: Source Management, Embeddings, Store, Retrieval, and CLI

**Files:**
- Create: `src/xrpl_rag/docs_source.py`
- Create: `src/xrpl_rag/embeddings.py`
- Create: `src/xrpl_rag/store.py`
- Create: `src/xrpl_rag/retrieval.py`
- Create: `src/xrpl_rag/cli.py`
- Create: `tests/test_docs_source.py`
- Create: `tests/test_retrieval.py`

**Interfaces:**
- Produces: `ensure_docs_repo(path: Path, repo_url: str, update: bool) -> Path`
- Produces: `LocalEmbeddingFunction(model_name: str)`
- Produces: `VectorStore`
- Produces: `retrieve(query: str, config: RagConfig, top_k: int) -> list[SearchResult]`
- Produces: Typer app with `ingest`, `search`, and `context`.

- [ ] **Step 1: Write failing tests for local path validation and retrieval mapping**

Tests should avoid real Chroma and sentence-transformer downloads by using small fake collection/query objects where needed.

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest tests/test_docs_source.py tests/test_retrieval.py -v`
Expected: FAIL because modules do not exist.

- [ ] **Step 3: Implement docs source and integration modules**

Implement clone/update with `git`, validation for local paths, lazy imports for ChromaDB and sentence-transformers, vector upsert by stable IDs, and CLI command wiring.

- [ ] **Step 4: Run all tests**

Run: `python -m pytest -v`
Expected: PASS.

### Task 6: Documentation and Smoke Verification

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: all CLI commands.

- [ ] **Step 1: Document usage**

Add install, ingest, search, context, local LLM handoff examples, and environment overrides.

- [ ] **Step 2: Run static CLI smoke checks**

Run: `python -m xrpl_rag.cli --help`
Expected: Typer help output with `ingest`, `search`, and `context`.

Run: `python -m pytest -v`
Expected: PASS.
