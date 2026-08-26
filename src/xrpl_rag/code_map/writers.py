from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Sequence

from xrpl_rag.code_map.models import CodeRecord


OUTPUT_FORMATS = {"jsonl", "markdown", "both"}


def write_jsonl(records: Sequence[CodeRecord], output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record.to_dict(), separators=(",", ":")) + "\n")
    return len(records)


def write_markdown(records: Sequence[CodeRecord], output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    by_file: defaultdict[str, list[CodeRecord]] = defaultdict(list)
    for record in records:
        by_file[record.file].append(record)

    for source_file, file_records in by_file.items():
        output_path = output_dir / f"{source_file}.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(_markdown_for_records(file_records), encoding="utf-8")
    return len(records)


def write_outputs(
    records: Sequence[CodeRecord], out_dir: Path, output_format: str
) -> dict[str, Path]:
    if output_format not in OUTPUT_FORMATS:
        raise ValueError(
            f"Unsupported output format {output_format!r}; use jsonl, markdown, or both."
        )

    outputs: dict[str, Path] = {}
    if output_format in {"jsonl", "both"}:
        jsonl_path = out_dir / "records.jsonl"
        write_jsonl(records, jsonl_path)
        outputs["jsonl"] = jsonl_path
    if output_format in {"markdown", "both"}:
        markdown_dir = out_dir / "markdown"
        write_markdown(records, markdown_dir)
        outputs["markdown"] = markdown_dir
    return outputs


def _markdown_for_records(records: Sequence[CodeRecord]) -> str:
    sections = [_markdown_for_record(record) for record in records]
    return "\n\n".join(sections).rstrip() + "\n"


def _markdown_for_record(record: CodeRecord) -> str:
    language = "cpp" if record.language == "cpp" else record.language
    return "\n".join(
        [
            f"## {_title(record.kind)}: {record.qualified_name}",
            "",
            f"File: {record.file}:{record.line_start}",
            f"Class: {record.class_name}",
            f"Namespace: {record.namespace}",
            f"Signature: {record.signature}",
            f"Docstring: {record.docstring}",
            "Imports:",
            *_list_lines(record.imports),
            "Calls:",
            *_list_lines(record.calls),
            "Called by:",
            *_list_lines(record.called_by),
            "Related Tests:",
            *_list_lines(record.related_tests),
            "",
            f"```{language}",
            record.code,
            "```",
        ]
    )


def _list_lines(values: Sequence[str]) -> list[str]:
    if not values:
        return ["- None"]
    return [f"- {value}" for value in values]


def _title(kind: str) -> str:
    return kind.replace("_", " ").title()
