from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterable


XRPL_DOCS_REPO_URL = "https://github.com/XRPLF/xrpl-dev-portal.git"
SKIP_DIRS = {".git", ".next", ".venv", "node_modules", "vendor"}


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
    files = [
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix.lower() in {".md", ".mdx"}
        and not _has_skipped_part(path.relative_to(root))
    ]
    yield from sorted(files)


def _has_skipped_part(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)

