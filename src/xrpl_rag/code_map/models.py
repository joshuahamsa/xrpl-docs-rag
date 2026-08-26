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


def make_record_id(
    file: str, kind: str, qualified_name: str, line_start: int, code: str
) -> str:
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
