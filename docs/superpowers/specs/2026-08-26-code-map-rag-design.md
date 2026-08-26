# Code Map RAG Design

## Goal

Build a local-first codebase mapper that analyzes a supplied source repository and emits structured records suitable for RAG. The first useful target is `xrpld`, but the design should support additional language analyzers over time.

The mapper produces both machine-ready JSONL and optional Markdown review files. Each entry captures the code unit, its source context, direct relationships, and enough text to embed without relying on a hosted LLM.

## Interface

Add a CLI command:

```bash
xrpl-rag map-code /path/to/codebase --out .rag/code-map --format both
```

Options:

- `codebase_path`: required path to the repository or source tree to map.
- `--out`: output directory, defaulting to `.rag/code-map`.
- `--format`: one of `jsonl`, `markdown`, or `both`; default `both`.
- `--include`: optional glob patterns for source files.
- `--exclude`: optional glob patterns layered on top of defaults.
- `--max-code-chars`: optional limit for stored code snippets to keep records embeddable.

The first implementation writes artifacts only. It does not automatically ingest the records into Chroma, because code records need their own collection name and retrieval formatting in a later step.

## Output

Primary output:

```text
.rag/code-map/records.jsonl
```

Optional review output:

```text
.rag/code-map/markdown/<relative-source-path>.md
```

Each JSONL record represents one discovered code unit, such as a function, method, class, struct, enum, namespace-level variable, or file summary. Function and class records are the first priority.

Example record:

```json
{
  "record_id": "sha256...",
  "kind": "function",
  "language": "cpp",
  "name": "read",
  "qualified_name": "ripple::Ledger::read",
  "file": "src/ripple/ledger/Ledger.cpp",
  "line_start": 120,
  "line_end": 188,
  "class": "Ledger",
  "namespace": "ripple",
  "signature": "std::shared_ptr<Ledger const> Ledger::read(...)",
  "docstring": "Best-effort preceding comment text.",
  "imports": ["ripple/ledger/Ledger.h", "ripple/basics/Log.h"],
  "code": "...",
  "calls": ["make_shared", "loadByIndex"],
  "called_by": ["ripple::LedgerMaster::getLedgerBySeq"],
  "related_tests": ["src/test/ledger/Ledger_test.cpp"],
  "embedding_text": "..."
}
```

Markdown output mirrors this structure with headings that make spot checks easy:

~~~text
## Function: ripple::Ledger::read

File: src/ripple/ledger/Ledger.cpp:120
Class: Ledger
Docstring: ...
Imports:
- ...
Called by:
- ...
Related Tests:
- ...

```cpp
...
```
~~~

## Architecture

Add a `xrpl_rag.code_map` package with focused modules:

- `models.py`: dataclasses for source files, code records, locations, and relationships.
- `scanner.py`: walks the supplied source tree, applies ignore rules, and yields source files with detected language.
- `analyzers/base.py`: protocol for language analyzers.
- `analyzers/cpp.py`: C/C++ analyzer for the first version.
- `relationships.py`: builds call, called-by, and related-test links across records.
- `writers.py`: writes JSONL and Markdown outputs.
- `cli.py`: wires the `map-code` command into the existing Typer app.

The pipeline is:

1. Scan source files.
2. Analyze each file into records with local file context.
3. Build cross-record relationships.
4. Create embedding text for each record.
5. Write JSONL and Markdown artifacts.

## Scanner

The scanner detects language by extension and skips directories that are rarely useful for source RAG:

- `.git`
- build directories such as `build`, `cmake-build-*`, `bazel-*`
- dependency directories such as `node_modules`, `vendor`, and `third_party`
- generated cache directories such as `.cache`, `.rag`, `__pycache__`

For C/C++, include:

- `.c`, `.cc`, `.cpp`, `.cxx`
- `.h`, `.hh`, `.hpp`, `.hxx`

The scanner returns paths relative to the supplied codebase root so records remain portable.

## C++ Analyzer

The first analyzer is deterministic and testable, using conservative text parsing rather than a native parser dependency. Tree-sitter is a future extension, not a requirement for the first implementation.

The analyzer extracts:

- includes/imports from `#include` lines.
- namespaces from lexical context.
- class and struct declarations.
- function and method definitions with signatures, line ranges, body code, and preceding comments.
- enum declarations where straightforward.
- calls inside function bodies using simple token patterns.

The analyzer avoids overclaiming precision. If a relationship cannot be resolved confidently, it keeps the raw call token in `calls` and leaves `called_by` resolution to the relationship builder.

## Relationships

The relationship builder works in two passes:

1. Build a symbol index from discovered records:
   - exact qualified names.
   - unqualified names.
   - class-qualified method names.
2. Resolve each function record's `calls` list to likely known records.

`called_by` is derived from resolved call edges.

For ambiguous symbols, keep the unqualified call name in `calls` and include only high-confidence matches in `called_by`. This protects RAG quality from false relationships.

## Related Tests

The first version links tests with deterministic heuristics:

- files under common test directories: `test`, `tests`, `unittest`, `unit_tests`, `src/test`.
- filenames containing `_test`, `Test`, or `Tests`.
- mirrored paths, such as `src/ripple/ledger/Ledger.cpp` matching `src/test/ledger/Ledger_test.cpp`.
- symbol-name matches in test source text.
- class or function name matches in test filenames.

The record stores related test file paths, not full test code, unless those files are separately mapped into their own records.

## Embedding Text

Each record gets an `embedding_text` field built from stable labels:

```text
Kind: function
Name: ripple::Ledger::read
File: src/ripple/ledger/Ledger.cpp:120-188
Class: Ledger
Namespace: ripple
Signature: ...
Docstring: ...
Imports: ...
Calls: ...
Called by: ...
Related tests: ...

Code:
...
```

This mirrors the user's desired RAG-entry shape while keeping JSONL fields structured for filtering.

## Error Handling

The CLI fails with actionable messages when:

- the supplied codebase path does not exist.
- no supported source files are found.
- output cannot be written.
- no analyzer exists for any scanned source file.

Individual unreadable or undecodable files are skipped with a warning rather than failing the whole run.

## Testing

Tests should use small local fixtures and avoid network calls.

Coverage should include:

- scanner include/exclude behavior.
- C++ includes, namespaces, classes, methods, free functions, comments, and line ranges.
- call extraction and `called_by` derivation.
- related-test heuristics.
- JSONL writer output.
- Markdown writer output.
- CLI command behavior on a small fixture repository.

## Out Of Scope

This first version does not include:

- hosted LLM summarization.
- automatic ingestion into the existing docs Chroma collection.
- perfect C++ semantic resolution.
- build-system aware compilation databases.
- macro expansion.
- incremental diff indexing.
- a web UI.

## Future Extensions

Useful later additions:

- Tree-sitter as the default analyzer backend.
- `compile_commands.json` support for better C++ symbol resolution.
- Python and TypeScript analyzers.
- separate Chroma collection for code records.
- combined docs-plus-code retrieval formatting.
- optional LLM-generated summaries stored separately from deterministic fields.
