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
