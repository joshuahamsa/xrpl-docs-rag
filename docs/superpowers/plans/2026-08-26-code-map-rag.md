# Code Map RAG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local-first codebase mapper that emits JSONL and Markdown RAG entries for supplied C/C++ codebases, with a language-pluggable structure for future analyzers.

**Architecture:** Add a focused `xrpl_rag.code_map` package. The pipeline scans source files, analyzes each file into deterministic records, builds cross-record relationships, creates embedding text, and writes JSONL plus Markdown artifacts through a new `xrpl-rag map-code` CLI command.

**Tech Stack:** Python 3.10+, standard library dataclasses/json/pathlib/re/fnmatch, Typer for CLI wiring, pytest for tests. No hosted LLM calls and no new parser dependency in the first version.

**Spec:** `docs/superpowers/specs/2026-08-26-code-map-rag-design.md`

## Global Constraints

- First useful target is `xrpld`; design supports additional language analyzers over time.
- Output formats are `jsonl`, `markdown`, and `both`; default is `both`.
- Primary JSONL output path is `.rag/code-map/records.jsonl`.
- Optional Markdown output path is `.rag/code-map/markdown/<relative-source-path>.md`.
- First implementation writes artifacts only and does not ingest records into Chroma.
- C/C++ analyzer uses conservative deterministic text parsing, not Tree-sitter.
- Individual unreadable or undecodable files are skipped with a warning rather than failing the whole run.
- Tests use small local fixtures and avoid network calls.

---

### Task 1: Code Map Models And Scanner

**Files:**
- Create: `src/xrpl_rag/code_map/__init__.py`
- Create: `src/xrpl_rag/code_map/models.py`
- Create: `src/xrpl_rag/code_map/scanner.py`
- Test: `tests/test_code_map_scanner.py`

**Interfaces:**
- Produces: `SourceFile(root: Path, path: Path, relative_path: str, language: str)`.
- Produces: `CodeRecord` dataclass with fields `record_id`, `kind`, `language`, `name`, `qualified_name`, `file`, `line_start`, `line_end`, `class_name`, `namespace`, `signature`, `docstring`, `imports`, `code`, `calls`, `called_by`, `related_tests`, and method `to_dict() -> dict[str, object]`.
- Produces: `scan_source_files(root: Path, include: Sequence[str] | None = None, exclude: Sequence[str] | None = None) -> list[SourceFile]`.
- Later tasks consume `SourceFile` and `CodeRecord`.

- [ ] **Step 1: Write failing scanner and model tests**

Create `tests/test_code_map_scanner.py`:

```python
from pathlib import Path

from xrpl_rag.code_map.models import CodeRecord
from xrpl_rag.code_map.scanner import scan_source_files


def test_scan_source_files_detects_cpp_and_skips_defaults(tmp_path):
    root = tmp_path / "repo"
    (root / "src").mkdir(parents=True)
    (root / "src" / "Ledger.cpp").write_text("int main() { return 0; }", encoding="utf-8")
    (root / "src" / "Ledger.h").write_text("#pragma once\n", encoding="utf-8")
    (root / "build").mkdir()
    (root / "build" / "Generated.cpp").write_text("void generated() {}", encoding="utf-8")
    (root / ".rag").mkdir()
    (root / ".rag" / "records.cpp").write_text("void cached() {}", encoding="utf-8")

    files = scan_source_files(root)

    assert [file.relative_path for file in files] == ["src/Ledger.cpp", "src/Ledger.h"]
    assert {file.language for file in files} == {"cpp"}


def test_scan_source_files_applies_include_and_exclude_globs(tmp_path):
    root = tmp_path / "repo"
    (root / "src").mkdir(parents=True)
    (root / "test").mkdir()
    (root / "src" / "A.cpp").write_text("void a() {}", encoding="utf-8")
    (root / "src" / "B.cpp").write_text("void b() {}", encoding="utf-8")
    (root / "test" / "A_test.cpp").write_text("void test_a() {}", encoding="utf-8")

    files = scan_source_files(root, include=["src/*.cpp"], exclude=["**/B.cpp"])

    assert [file.relative_path for file in files] == ["src/A.cpp"]


def test_code_record_to_dict_uses_json_field_names():
    record = CodeRecord(
        record_id="abc",
        kind="function",
        language="cpp",
        name="read",
        qualified_name="ripple::Ledger::read",
        file="src/Ledger.cpp",
        line_start=3,
        line_end=8,
        class_name="Ledger",
        namespace="ripple",
        signature="void Ledger::read()",
        docstring="Reads a ledger.",
        imports=["ripple/Ledger.h"],
        code="void Ledger::read() {}",
        calls=["load"],
    )

    assert record.to_dict()["class"] == "Ledger"
    assert record.to_dict()["called_by"] == []
    assert "class_name" not in record.to_dict()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_code_map_scanner.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'xrpl_rag.code_map'`.

- [ ] **Step 3: Implement models and scanner**

Create `src/xrpl_rag/code_map/__init__.py`:

```python
"""Codebase mapping utilities for RAG records."""
```

Create `src/xrpl_rag/code_map/models.py` with:

```python
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, replace
from pathlib import Path


@dataclass(frozen=True)
class SourceFile:
    root: Path
    path: Path
    relative_path: str
    language: str


@dataclass(frozen=True)
class CodeRecord:
    record_id: str
    kind: str
    language: str
    name: str
    qualified_name: str
    file: str
    line_start: int
    line_end: int
    class_name: str = ""
    namespace: str = ""
    signature: str = ""
    docstring: str = ""
    imports: list[str] = field(default_factory=list)
    code: str = ""
    calls: list[str] = field(default_factory=list)
    called_by: list[str] = field(default_factory=list)
    related_tests: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "record_id": self.record_id,
            "kind": self.kind,
            "language": self.language,
            "name": self.name,
            "qualified_name": self.qualified_name,
            "file": self.file,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "class": self.class_name,
            "namespace": self.namespace,
            "signature": self.signature,
            "docstring": self.docstring,
            "imports": list(self.imports),
            "code": self.code,
            "calls": list(self.calls),
            "called_by": list(self.called_by),
            "related_tests": list(self.related_tests),
            "embedding_text": embedding_text(self),
        }

    def with_relationships(
        self, called_by: list[str], related_tests: list[str]
    ) -> "CodeRecord":
        return replace(self, called_by=called_by, related_tests=related_tests)


def make_record_id(file: str, kind: str, qualified_name: str, line_start: int, code: str) -> str:
    value = f"{file}\0{kind}\0{qualified_name}\0{line_start}\0{code}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def embedding_text(record: CodeRecord) -> str:
    labels = [
        f"Kind: {record.kind}",
        f"Name: {record.qualified_name or record.name}",
        f"File: {record.file}:{record.line_start}-{record.line_end}",
        f"Class: {record.class_name}",
        f"Namespace: {record.namespace}",
        f"Signature: {record.signature}",
        f"Docstring: {record.docstring}",
        f"Imports: {', '.join(record.imports)}",
        f"Calls: {', '.join(record.calls)}",
        f"Called by: {', '.join(record.called_by)}",
        f"Related tests: {', '.join(record.related_tests)}",
        "",
        "Code:",
        record.code,
    ]
    return "\n".join(labels).strip()
```

Create `src/xrpl_rag/code_map/scanner.py` with:

```python
from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Sequence

from xrpl_rag.code_map.models import SourceFile


CPP_EXTENSIONS = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx"}
DEFAULT_EXCLUDED_DIRS = {
    ".git",
    ".cache",
    ".rag",
    "__pycache__",
    "build",
    "node_modules",
    "vendor",
    "third_party",
}
DEFAULT_EXCLUDED_PREFIXES = ("cmake-build-", "bazel-")


def scan_source_files(
    root: Path,
    include: Sequence[str] | None = None,
    exclude: Sequence[str] | None = None,
) -> list[SourceFile]:
    root = root.resolve()
    files: list[SourceFile] = []
    include_patterns = list(include or [])
    exclude_patterns = list(exclude or [])

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative_path = path.relative_to(root).as_posix()
        if _is_under_default_excluded_dir(relative_path):
            continue
        if include_patterns and not _matches_any(relative_path, include_patterns):
            continue
        if exclude_patterns and _matches_any(relative_path, exclude_patterns):
            continue
        language = _detect_language(path)
        if language:
            files.append(
                SourceFile(
                    root=root,
                    path=path,
                    relative_path=relative_path,
                    language=language,
                )
            )
    return files


def _detect_language(path: Path) -> str:
    return "cpp" if path.suffix.lower() in CPP_EXTENSIONS else ""


def _is_under_default_excluded_dir(relative_path: str) -> bool:
    for part in Path(relative_path).parts[:-1]:
        if part in DEFAULT_EXCLUDED_DIRS:
            return True
        if any(part.startswith(prefix) for prefix in DEFAULT_EXCLUDED_PREFIXES):
            return True
    return False


def _matches_any(relative_path: str, patterns: Sequence[str]) -> bool:
    return any(
        fnmatch.fnmatch(relative_path, pattern)
        or fnmatch.fnmatch(Path(relative_path).name, pattern)
        for pattern in patterns
    )
```

- [ ] **Step 4: Run scanner tests**

Run: `.venv/bin/python -m pytest tests/test_code_map_scanner.py -v`

Expected: PASS.

### Task 2: C++ Analyzer

**Files:**
- Create: `src/xrpl_rag/code_map/analyzers/__init__.py`
- Create: `src/xrpl_rag/code_map/analyzers/base.py`
- Create: `src/xrpl_rag/code_map/analyzers/cpp.py`
- Test: `tests/test_code_map_cpp_analyzer.py`

**Interfaces:**
- Consumes: `SourceFile` and `CodeRecord` from Task 1.
- Produces: `Analyzer` protocol with `language: str` and `analyze(source_file: SourceFile, max_code_chars: int = 12000) -> list[CodeRecord]`.
- Produces: `CppAnalyzer().analyze(source_file, max_code_chars=12000) -> list[CodeRecord]`.
- Later tasks consume C++ records with populated imports, classes, methods, free functions, calls, docstrings, and line ranges.

- [ ] **Step 1: Write failing analyzer tests**

Create `tests/test_code_map_cpp_analyzer.py`:

```python
from xrpl_rag.code_map.analyzers.cpp import CppAnalyzer
from xrpl_rag.code_map.models import SourceFile


def test_cpp_analyzer_extracts_class_method_free_function_and_calls(tmp_path):
    root = tmp_path / "repo"
    source_path = root / "src" / "Ledger.cpp"
    source_path.parent.mkdir(parents=True)
    source_path.write_text(
        """#include <memory>
#include "ripple/ledger/Ledger.h"

namespace ripple {

class Ledger {
public:
    void read();
};

// Reads the ledger from storage.
void Ledger::read()
{
    loadByIndex();
    helper();
}

int helper()
{
    return 1;
}

} // namespace ripple
""",
        encoding="utf-8",
    )
    source_file = SourceFile(root, source_path, "src/Ledger.cpp", "cpp")

    records = CppAnalyzer().analyze(source_file)

    class_record = next(record for record in records if record.kind == "class")
    method_record = next(record for record in records if record.qualified_name == "ripple::Ledger::read")
    function_record = next(record for record in records if record.qualified_name == "ripple::helper")

    assert class_record.name == "Ledger"
    assert class_record.namespace == "ripple"
    assert method_record.class_name == "Ledger"
    assert method_record.docstring == "Reads the ledger from storage."
    assert method_record.imports == ["memory", "ripple/ledger/Ledger.h"]
    assert method_record.calls == ["loadByIndex", "helper"]
    assert "void Ledger::read()" in method_record.signature
    assert method_record.line_start == 12
    assert function_record.calls == []


def test_cpp_analyzer_truncates_code_without_losing_record_extent(tmp_path):
    root = tmp_path / "repo"
    source_path = root / "Long.cpp"
    source_path.parent.mkdir(parents=True)
    source_path.write_text(
        "void longFunction()\\n{\\n"
        + "\\n".join(f"    call{i}();" for i in range(20))
        + "\\n}\\n",
        encoding="utf-8",
    )
    source_file = SourceFile(root, source_path, "Long.cpp", "cpp")

    record = CppAnalyzer().analyze(source_file, max_code_chars=80)[0]

    assert record.qualified_name == "longFunction"
    assert record.line_end == 23
    assert len(record.code) <= 80
    assert record.code.endswith("[truncated]")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_code_map_cpp_analyzer.py -v`

Expected: FAIL with missing analyzer module.

- [ ] **Step 3: Implement analyzer protocol and C++ analyzer**

Create `src/xrpl_rag/code_map/analyzers/__init__.py`:

```python
"""Language analyzers for code mapping."""
```

Create `src/xrpl_rag/code_map/analyzers/base.py`:

```python
from __future__ import annotations

from typing import Protocol

from xrpl_rag.code_map.models import CodeRecord, SourceFile


class Analyzer(Protocol):
    language: str

    def analyze(
        self, source_file: SourceFile, max_code_chars: int = 12_000
    ) -> list[CodeRecord]:
        ...
```

Create `src/xrpl_rag/code_map/analyzers/cpp.py` using deterministic text parsing:

```python
from __future__ import annotations

import re

from xrpl_rag.code_map.models import CodeRecord, SourceFile, make_record_id


INCLUDE_RE = re.compile(r"^\s*#include\s+[<\"]([^>\"]+)[>\"]")
NAMESPACE_RE = re.compile(r"^\s*namespace\s+([A-Za-z_]\w*)\s*\{")
CLASS_RE = re.compile(r"^\s*(class|struct)\s+([A-Za-z_]\w*)\b")
CALL_RE = re.compile(r"\b([A-Za-z_]\w*)\s*\(")
CONTROL_WORDS = {
    "if",
    "for",
    "while",
    "switch",
    "return",
    "sizeof",
    "static_cast",
    "dynamic_cast",
    "reinterpret_cast",
    "const_cast",
    "catch",
}


class CppAnalyzer:
    language = "cpp"

    def analyze(
        self, source_file: SourceFile, max_code_chars: int = 12_000
    ) -> list[CodeRecord]:
        try:
            text = source_file.path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return []

        lines = text.splitlines()
        imports = _extract_imports(lines)
        namespace_by_line = _namespace_context(lines)
        class_records = _extract_classes(source_file, lines, imports, namespace_by_line)
        function_records = _extract_functions(
            source_file, lines, imports, namespace_by_line, max_code_chars
        )
        return class_records + function_records
```

Then implement helpers:

```python
def _extract_imports(lines: list[str]) -> list[str]:
    imports: list[str] = []
    for line in lines:
        match = INCLUDE_RE.match(line)
        if match:
            imports.append(match.group(1))
    return imports
```

`_namespace_context(lines)` tracks brace depth and namespace names per 1-based line. It pushes `(brace_depth, name)` when matching `namespace name {` and pops when line brace depth falls below the namespace's opening depth. It returns `dict[int, str]` mapping line number to joined namespace string.

`_extract_classes(...)` creates class/struct records at declaration lines. For each match, find the declaration extent by scanning until the first line containing `};`; if none is found, use the declaration line only. Qualified name is `namespace::Class` when a namespace exists. Code is the declaration extent.

`_extract_functions(...)` scans for top-level definition starts. It combines contiguous signature lines until a line containing `{`, skips signatures ending in `;`, skips class/control statements, and balances braces until the definition ends. Function name comes from the final token before `(`, preserving class qualifiers such as `Ledger::read`. Namespace is the namespace at the start line. Class name is the qualifier before the last `::` when present. Qualified name is `namespace::signature_name`. Docstring comes from immediately preceding `//` lines or `/* ... */` block comments. Calls are unique call tokens found in the function body, excluding the function's own unqualified name and control words.

Use `_truncate_code(code, max_code_chars)` to append `"[truncated]"` while keeping `len(code) <= max_code_chars`.

- [ ] **Step 4: Run analyzer tests**

Run: `.venv/bin/python -m pytest tests/test_code_map_cpp_analyzer.py -v`

Expected: PASS.

### Task 3: Relationship Builder

**Files:**
- Create: `src/xrpl_rag/code_map/relationships.py`
- Test: `tests/test_code_map_relationships.py`

**Interfaces:**
- Consumes: `CodeRecord`.
- Produces: `build_relationships(records: Sequence[CodeRecord], source_files: Sequence[SourceFile] | None = None) -> list[CodeRecord]`.
- Later tasks consume records with `called_by` and `related_tests` populated.

- [ ] **Step 1: Write failing relationship tests**

Create `tests/test_code_map_relationships.py`:

```python
from xrpl_rag.code_map.models import CodeRecord, SourceFile
from xrpl_rag.code_map.relationships import build_relationships


def make_record(name, qualified_name, file, calls=None, class_name=""):
    return CodeRecord(
        record_id=qualified_name,
        kind="function",
        language="cpp",
        name=name,
        qualified_name=qualified_name,
        file=file,
        line_start=1,
        line_end=3,
        class_name=class_name,
        code=f"void {name}() {{}}",
        calls=calls or [],
    )


def test_build_relationships_derives_called_by_for_unambiguous_calls():
    read = make_record("read", "ripple::Ledger::read", "src/ripple/ledger/Ledger.cpp", ["helper"])
    helper = make_record("helper", "ripple::helper", "src/ripple/ledger/Helpers.cpp")
    other = make_record("main", "ripple::main", "src/main.cpp", ["read"])

    records = build_relationships([read, helper, other])

    by_name = {record.qualified_name: record for record in records}
    assert by_name["ripple::helper"].called_by == ["ripple::Ledger::read"]
    assert by_name["ripple::Ledger::read"].called_by == ["ripple::main"]


def test_build_relationships_ignores_ambiguous_unqualified_calls():
    caller = make_record("caller", "caller", "caller.cpp", ["shared"])
    first = make_record("shared", "a::shared", "a.cpp")
    second = make_record("shared", "b::shared", "b.cpp")

    records = build_relationships([caller, first, second])

    assert all(record.called_by == [] for record in records)


def test_build_relationships_links_related_tests_by_path_and_symbol(tmp_path):
    root = tmp_path / "repo"
    source = root / "src" / "ripple" / "ledger" / "Ledger.cpp"
    test = root / "src" / "test" / "ledger" / "Ledger_test.cpp"
    source.parent.mkdir(parents=True)
    test.parent.mkdir(parents=True)
    source.write_text("void read() {}", encoding="utf-8")
    test.write_text("void test_read() { read(); }", encoding="utf-8")
    record = make_record("read", "ripple::Ledger::read", "src/ripple/ledger/Ledger.cpp", class_name="Ledger")
    source_file = SourceFile(root, source, "src/ripple/ledger/Ledger.cpp", "cpp")
    test_file = SourceFile(root, test, "src/test/ledger/Ledger_test.cpp", "cpp")

    records = build_relationships([record], [source_file, test_file])

    assert records[0].related_tests == ["src/test/ledger/Ledger_test.cpp"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_code_map_relationships.py -v`

Expected: FAIL with missing `relationships` module.

- [ ] **Step 3: Implement relationships**

Create `src/xrpl_rag/code_map/relationships.py` with:

```python
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Sequence

from xrpl_rag.code_map.models import CodeRecord, SourceFile


TEST_DIR_NAMES = {"test", "tests", "unittest", "unit_tests"}
TEST_NAME_TOKENS = ("_test", "test", "tests")


def build_relationships(
    records: Sequence[CodeRecord], source_files: Sequence[SourceFile] | None = None
) -> list[CodeRecord]:
    called_by = _build_called_by(records)
    related_tests = _build_related_tests(records, source_files or [])
    return [
        record.with_relationships(
            sorted(called_by.get(record.qualified_name, set())),
            sorted(related_tests.get(record.qualified_name, set())),
        )
        for record in records
    ]
```

Implement `_build_called_by(records)` so it indexes `qualified_name`, `name`, and `class_name::name` for function records. A call resolves only when its candidate set has exactly one qualified name. Add the caller's `qualified_name` to the callee's `called_by`.

Implement `_build_related_tests(records, source_files)` so it filters test files, reads their text as UTF-8, and links test relative paths when any of these match:

- record `name` appears in the test text.
- record `class_name` appears in the test text or test filename.
- source stem appears in test filename.
- source parent basename appears in test path and class/function name appears in test filename.

Unreadable or undecodable test files are ignored.

- [ ] **Step 4: Run relationship tests**

Run: `.venv/bin/python -m pytest tests/test_code_map_relationships.py -v`

Expected: PASS.

### Task 4: Writers

**Files:**
- Create: `src/xrpl_rag/code_map/writers.py`
- Test: `tests/test_code_map_writers.py`

**Interfaces:**
- Consumes: `CodeRecord`.
- Produces: `write_jsonl(records: Sequence[CodeRecord], output_path: Path) -> int`.
- Produces: `write_markdown(records: Sequence[CodeRecord], output_dir: Path) -> int`.
- Produces: `write_outputs(records: Sequence[CodeRecord], out_dir: Path, output_format: str) -> dict[str, Path]`.
- CLI consumes `write_outputs`.

- [ ] **Step 1: Write failing writer tests**

Create `tests/test_code_map_writers.py`:

```python
import json

from xrpl_rag.code_map.models import CodeRecord
from xrpl_rag.code_map.writers import write_jsonl, write_markdown, write_outputs


def sample_record():
    return CodeRecord(
        record_id="abc",
        kind="function",
        language="cpp",
        name="read",
        qualified_name="ripple::Ledger::read",
        file="src/ripple/ledger/Ledger.cpp",
        line_start=12,
        line_end=16,
        class_name="Ledger",
        namespace="ripple",
        signature="void Ledger::read()",
        docstring="Reads the ledger.",
        imports=["ripple/ledger/Ledger.h"],
        code="void Ledger::read() {}",
        calls=["helper"],
        called_by=["ripple::main"],
        related_tests=["src/test/ledger/Ledger_test.cpp"],
    )


def test_write_jsonl_writes_one_record_per_line(tmp_path):
    output_path = tmp_path / "records.jsonl"

    count = write_jsonl([sample_record()], output_path)

    assert count == 1
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["qualified_name"] == "ripple::Ledger::read"
    assert payload["class"] == "Ledger"
    assert "Kind: function" in payload["embedding_text"]


def test_write_markdown_groups_records_by_source_file(tmp_path):
    count = write_markdown([sample_record()], tmp_path / "markdown")

    output = tmp_path / "markdown" / "src" / "ripple" / "ledger" / "Ledger.cpp.md"
    assert count == 1
    text = output.read_text(encoding="utf-8")
    assert "## Function: ripple::Ledger::read" in text
    assert "File: src/ripple/ledger/Ledger.cpp:12" in text
    assert "- ripple/ledger/Ledger.h" in text
    assert "```cpp" in text


def test_write_outputs_respects_format(tmp_path):
    outputs = write_outputs([sample_record()], tmp_path, "jsonl")

    assert outputs == {"jsonl": tmp_path / "records.jsonl"}
    assert (tmp_path / "records.jsonl").exists()
    assert not (tmp_path / "markdown").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_code_map_writers.py -v`

Expected: FAIL with missing writers module.

- [ ] **Step 3: Implement writers**

Create `src/xrpl_rag/code_map/writers.py` with JSONL and Markdown writers. Requirements:

- `write_jsonl` creates parent dirs, writes sorted records in input order, one compact JSON object per line, UTF-8, and returns count.
- `write_markdown` groups by `record.file`, writes to `output_dir / f"{record.file}.md"`, creates parent dirs, and returns record count.
- `write_outputs` validates `output_format in {"jsonl", "markdown", "both"}` and returns paths for outputs written.
- Markdown headings use `## {Kind Title}: {qualified_name}`.
- Empty lists render as `- None`.

- [ ] **Step 4: Run writer tests**

Run: `.venv/bin/python -m pytest tests/test_code_map_writers.py -v`

Expected: PASS.

### Task 5: Pipeline And CLI

**Files:**
- Create: `src/xrpl_rag/code_map/pipeline.py`
- Modify: `src/xrpl_rag/cli.py`
- Modify: `README.md`
- Test: `tests/test_code_map_pipeline_cli.py`

**Interfaces:**
- Consumes: `scan_source_files`, `CppAnalyzer`, `build_relationships`, and `write_outputs`.
- Produces: `map_codebase(root: Path, out_dir: Path, output_format: str = "both", include: Sequence[str] | None = None, exclude: Sequence[str] | None = None, max_code_chars: int = 12000) -> MapCodeResult`.
- Produces: `MapCodeResult(records: list[CodeRecord], source_files: list[SourceFile], outputs: dict[str, Path], warnings: list[str])`.
- Produces CLI command `xrpl-rag map-code CODEBASE_PATH --out .rag/code-map --format both --include PATTERN --exclude PATTERN --max-code-chars 12000`.

- [ ] **Step 1: Write failing pipeline and CLI tests**

Create `tests/test_code_map_pipeline_cli.py`:

```python
from typer.testing import CliRunner

from xrpl_rag.cli import app
from xrpl_rag.code_map.pipeline import map_codebase


def make_repo(tmp_path):
    root = tmp_path / "repo"
    source = root / "src" / "Ledger.cpp"
    test = root / "src" / "test" / "Ledger_test.cpp"
    source.parent.mkdir(parents=True)
    test.parent.mkdir(parents=True)
    source.write_text(
        """#include "Ledger.h"
namespace ripple {
void helper() {}
void read()
{
    helper();
}
}
""",
        encoding="utf-8",
    )
    test.write_text("void test_read() { read(); }", encoding="utf-8")
    return root


def test_map_codebase_writes_both_outputs(tmp_path):
    root = make_repo(tmp_path)
    out_dir = tmp_path / "out"

    result = map_codebase(root, out_dir)

    assert len(result.records) == 3
    assert result.outputs["jsonl"] == out_dir / "records.jsonl"
    assert result.outputs["markdown"] == out_dir / "markdown"
    assert (out_dir / "records.jsonl").exists()
    assert (out_dir / "markdown" / "src" / "Ledger.cpp.md").exists()
    read_record = next(record for record in result.records if record.qualified_name == "ripple::read")
    assert read_record.called_by == ["test_read"]
    assert read_record.related_tests == ["src/test/Ledger_test.cpp"]


def test_map_codebase_errors_when_root_missing(tmp_path):
    missing = tmp_path / "missing"

    try:
        map_codebase(missing, tmp_path / "out")
    except FileNotFoundError as exc:
        assert "Codebase path does not exist" in str(exc)
    else:
        raise AssertionError("Expected FileNotFoundError")


def test_cli_map_code_command(tmp_path):
    root = make_repo(tmp_path)
    out_dir = tmp_path / "out"
    runner = CliRunner()

    result = runner.invoke(app, ["map-code", str(root), "--out", str(out_dir), "--format", "jsonl"])

    assert result.exit_code == 0
    assert "Mapped" in result.output
    assert (out_dir / "records.jsonl").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_code_map_pipeline_cli.py -v`

Expected: FAIL with missing pipeline module or CLI command.

- [ ] **Step 3: Implement pipeline**

Create `src/xrpl_rag/code_map/pipeline.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from xrpl_rag.code_map.analyzers.cpp import CppAnalyzer
from xrpl_rag.code_map.models import CodeRecord, SourceFile
from xrpl_rag.code_map.relationships import build_relationships
from xrpl_rag.code_map.scanner import scan_source_files
from xrpl_rag.code_map.writers import write_outputs


@dataclass(frozen=True)
class MapCodeResult:
    records: list[CodeRecord]
    source_files: list[SourceFile]
    outputs: dict[str, Path]
    warnings: list[str]


def map_codebase(
    root: Path,
    out_dir: Path,
    output_format: str = "both",
    include: Sequence[str] | None = None,
    exclude: Sequence[str] | None = None,
    max_code_chars: int = 12_000,
) -> MapCodeResult:
    root = root.resolve()
    if not root.exists():
        raise FileNotFoundError(f"Codebase path does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Codebase path is not a directory: {root}")

    source_files = scan_source_files(root, include=include, exclude=exclude)
    if not source_files:
        raise RuntimeError(f"No supported source files found under {root}")

    analyzers = {"cpp": CppAnalyzer()}
    records: list[CodeRecord] = []
    warnings: list[str] = []
    for source_file in source_files:
        analyzer = analyzers.get(source_file.language)
        if analyzer is None:
            warnings.append(f"No analyzer for {source_file.relative_path}")
            continue
        file_records = analyzer.analyze(source_file, max_code_chars=max_code_chars)
        records.extend(file_records)

    if not records:
        raise RuntimeError(f"No code records produced under {root}")

    records = build_relationships(records, source_files)
    outputs = write_outputs(records, out_dir, output_format)
    return MapCodeResult(records, source_files, outputs, warnings)
```

- [ ] **Step 4: Wire CLI command**

Modify `src/xrpl_rag/cli.py` to import `map_codebase` and add:

```python
@app.command("map-code")
def map_code(
    codebase_path: Path = typer.Argument(..., help="Repository or source tree to map."),
    out_dir: Path = typer.Option(Path(".rag/code-map"), "--out", help="Output directory."),
    output_format: str = typer.Option(
        "both", "--format", help="Output format: jsonl, markdown, or both."
    ),
    include: list[str] | None = typer.Option(
        None, "--include", help="Glob pattern to include. Repeat for multiple patterns."
    ),
    exclude: list[str] | None = typer.Option(
        None, "--exclude", help="Glob pattern to exclude. Repeat for multiple patterns."
    ),
    max_code_chars: int = typer.Option(
        12_000, "--max-code-chars", min=200, help="Maximum code characters per record."
    ),
):
    try:
        result = map_codebase(
            codebase_path,
            out_dir,
            output_format=output_format,
            include=include,
            exclude=exclude,
            max_code_chars=max_code_chars,
        )
    except Exception as exc:
        typer.secho(f"map-code failed: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc

    typer.echo(
        f"Mapped {len(result.records)} records from {len(result.source_files)} files."
    )
    for name, path in result.outputs.items():
        typer.echo(f"{name}: {path}")
    for warning in result.warnings:
        typer.secho(f"warning: {warning}", fg=typer.colors.YELLOW, err=True)
```

- [ ] **Step 5: Update README**

Add a concise `Map A Codebase` section after `Create Local LLM Context`:

```markdown
## Map A Codebase

Create JSONL and Markdown records for a C/C++ source tree:

```bash
.venv/bin/xrpl-rag map-code /path/to/xrpld --out .rag/code-map --format both
```

The mapper writes `.rag/code-map/records.jsonl` plus Markdown review files under `.rag/code-map/markdown`. The first version uses deterministic C/C++ parsing and does not call hosted LLMs.
```

- [ ] **Step 6: Run pipeline and CLI tests**

Run: `.venv/bin/python -m pytest tests/test_code_map_pipeline_cli.py -v`

Expected: PASS.

### Task 6: Full Verification

**Files:**
- No new files.
- Verify: all code map tests and existing project tests.

**Interfaces:**
- Consumes all previous task outputs.
- Produces verified feature behavior.

- [ ] **Step 1: Run focused code map tests**

Run: `.venv/bin/python -m pytest tests/test_code_map_scanner.py tests/test_code_map_cpp_analyzer.py tests/test_code_map_relationships.py tests/test_code_map_writers.py tests/test_code_map_pipeline_cli.py -v`

Expected: PASS.

- [ ] **Step 2: Run full test suite**

Run: `.venv/bin/python -m pytest -v`

Expected: PASS.

- [ ] **Step 3: Run CLI help**

Run: `.venv/bin/python -m xrpl_rag.cli --help`

Expected: output includes `map-code`.

- [ ] **Step 4: Run a fixture smoke command**

Create a temporary fixture source tree in a shell temp directory, then run:

```bash
.venv/bin/xrpl-rag map-code "$TMPDIR/repo" --out "$TMPDIR/out" --format both
```

Expected: command exits 0 and writes `$TMPDIR/out/records.jsonl` plus `$TMPDIR/out/markdown`.
