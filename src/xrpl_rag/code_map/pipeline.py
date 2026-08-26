from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

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
    progress_callback: Callable[[str], None] | None = None,
    progress_every: int = 100,
    throttle_ms: int = 0,
) -> MapCodeResult:
    progress_every = max(1, progress_every)
    throttle_seconds = max(0, throttle_ms) / 1000

    root = root.resolve()
    if not root.exists():
        raise FileNotFoundError(f"Codebase path does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Codebase path is not a directory: {root}")

    _report(progress_callback, "Scanning source files...")
    source_files = scan_source_files(root, include=include, exclude=exclude)
    if not source_files:
        raise RuntimeError(f"No supported source files found under {root}")
    _report(progress_callback, f"Found {len(source_files)} supported source files.")

    analyzers = {"cpp": CppAnalyzer()}
    records: list[CodeRecord] = []
    warnings: list[str] = []
    for index, source_file in enumerate(source_files, start=1):
        analyzer = analyzers.get(source_file.language)
        if analyzer is None:
            warnings.append(f"No analyzer for {source_file.relative_path}")
            continue
        records.extend(analyzer.analyze(source_file, max_code_chars=max_code_chars))
        if index % progress_every == 0 or index == len(source_files):
            _report(
                progress_callback,
                f"Analyzed {index}/{len(source_files)} files, records={len(records)}.",
            )
        if throttle_seconds:
            time.sleep(throttle_seconds)

    if not records:
        raise RuntimeError(f"No code records produced under {root}")

    _report(progress_callback, "Building relationships...")
    records = build_relationships(records, source_files)
    _report(progress_callback, "Writing outputs...")
    outputs = write_outputs(records, out_dir, output_format)
    return MapCodeResult(records, source_files, outputs, warnings)


def _report(progress_callback: Callable[[str], None] | None, message: str) -> None:
    if progress_callback is not None:
        progress_callback(message)
