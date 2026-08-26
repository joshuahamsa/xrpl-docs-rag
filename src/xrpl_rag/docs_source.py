from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


XRPL_DOCS_REPO_URL = "https://github.com/XRPLF/xrpl-dev-portal.git"
XRPL_PY_REPO_URL = "https://github.com/XRPLF/xrpl-py.git"
XRPL_JS_REPO_URL = "https://github.com/XRPLF/xrpl.js.git"
SKIP_DIRS = {".git", ".next", ".venv", "assets", "node_modules", "vendor"}
DOC_SUFFIXES = {".html", ".md", ".mdx", ".rst"}
XRPL_DOC_SUFFIXES = frozenset({".md", ".mdx"})
XRPL_PY_SUFFIXES = frozenset({".md", ".py", ".rst"})
XRPL_JS_SUFFIXES = frozenset({".html", ".md"})


@dataclass(frozen=True)
class DocsSource:
    name: str
    repo_url: str
    path: Path
    url_base: str
    prefix_source_path: bool = False
    file_suffixes: frozenset[str] = frozenset(DOC_SUFFIXES)
    include_parts: tuple[str, ...] = ()
    source_url_base: str | None = None


DEFAULT_DOC_SOURCES = (
    DocsSource(
        name="xrpl-docs",
        repo_url=XRPL_DOCS_REPO_URL,
        path=Path(".cache/xrpl-dev-portal"),
        url_base="https://xrpl.org/docs/",
        file_suffixes=XRPL_DOC_SUFFIXES,
    ),
    DocsSource(
        name="xrpl-py",
        repo_url=XRPL_PY_REPO_URL,
        path=Path(".cache/xrpl-py"),
        url_base="https://xrpl-py.readthedocs.io/en/stable/",
        prefix_source_path=True,
        file_suffixes=XRPL_PY_SUFFIXES,
        include_parts=("docs", "xrpl"),
        source_url_base="https://github.com/XRPLF/xrpl-py/blob/main/",
    ),
    DocsSource(
        name="xrpl-js",
        repo_url=XRPL_JS_REPO_URL,
        path=Path(".cache/xrpl.js"),
        url_base="https://js.xrpl.org/",
        prefix_source_path=True,
        file_suffixes=XRPL_JS_SUFFIXES,
        include_parts=("docs", "packages", "README.md"),
    ),
)


def ensure_docs_repo(
    path: Path, update: bool = True, repo_url: str = XRPL_DOCS_REPO_URL
) -> Path:
    if path.exists():
        if update and (path / ".git").exists():
            subprocess.run(["git", "-C", str(path), "pull", "--ff-only"], check=True)
        return path

    if not update:
        raise FileNotFoundError(f"Docs path does not exist: {path}")

    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", "--depth", "1", repo_url, str(path)], check=True)
    return path


def iter_markdown_files(root: Path) -> Iterable[Path]:
    yield from _iter_files(root, {".md", ".mdx"})


def iter_document_files(
    root: Path,
    suffixes: Iterable[str] = DOC_SUFFIXES,
    include_parts: tuple[str, ...] = (),
) -> Iterable[Path]:
    yield from _iter_files(root, set(suffixes), include_parts)


def _iter_files(
    root: Path, suffixes: set[str], include_parts: tuple[str, ...] = ()
) -> Iterable[Path]:
    files = [
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix.lower() in suffixes
        and _is_included(path.relative_to(root), include_parts)
    ]
    yield from sorted(files)


def _is_included(path: Path, include_parts: tuple[str, ...]) -> bool:
    if _has_skipped_part(path):
        return False
    if not include_parts:
        return True
    return bool(path.parts and path.parts[0] in include_parts)


def _has_skipped_part(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)
