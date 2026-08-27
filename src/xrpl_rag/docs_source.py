from __future__ import annotations

import re
import subprocess
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


XRPL_DOCS_REPO_URL = "https://github.com/XRPLF/xrpl-dev-portal.git"
XRPL_PY_REPO_URL = "https://github.com/XRPLF/xrpl-py.git"
XRPL_JS_REPO_URL = "https://github.com/XRPLF/xrpl.js.git"
XAMAN_DOCS_REPO_URL = "https://github.com/XRPL-Labs/Developer-Help-Center.git"
JOEY_DOCS_LLMS_TXT_URL = "https://docs.joeywallet.xyz/llms.txt"
JOEY_DOCS_URL_BASE = "https://docs.joeywallet.xyz/"
XLS_STANDARDS_REPO_URL = "https://github.com/XRPLF/XRPL-Standards.git"
XRPL4J_REPO_URL = "https://github.com/XRPLF/xrpl4j.git"
XRPL_GO_REPO_URL = "https://github.com/XRPLF/xrpl-go.git"
CLIO_REPO_URL = "https://github.com/XRPLF/clio.git"
XAHAU_DOCS_REPO_URL = "https://github.com/Xahau/Xahau-Docs.git"
GEMWALLET_DOCS_REPO_URL = "https://github.com/GemWallet/gemwallet-website.git"
LEDGER_DOCS_LLMS_TXT_URL = "https://developers.ledger.com/llms.txt"
LEDGER_DOCS_URL_BASE = "https://developers.ledger.com/docs/"
SKIP_DIRS = {".git", ".gitbook", ".next", ".venv", "assets", "node_modules", "vendor"}
DOC_SUFFIXES = {".html", ".md", ".mdx", ".rst"}
XRPL_DOC_SUFFIXES = frozenset({".md", ".mdx"})
XRPL_PY_SUFFIXES = frozenset({".md", ".py", ".rst"})
XRPL_JS_SUFFIXES = frozenset({".html", ".md"})
MARKDOWN_SUFFIXES = frozenset({".md"})


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
    llms_txt_url: str | None = None


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
    DocsSource(
        name="xaman-docs",
        repo_url=XAMAN_DOCS_REPO_URL,
        path=Path(".cache/xaman-docs"),
        url_base="https://docs.xaman.dev/",
        prefix_source_path=True,
        file_suffixes=MARKDOWN_SUFFIXES,
    ),
    DocsSource(
        name="joey-docs",
        repo_url="",
        path=Path(".cache/joey-docs"),
        url_base=JOEY_DOCS_URL_BASE,
        prefix_source_path=True,
        file_suffixes=MARKDOWN_SUFFIXES,
        llms_txt_url=JOEY_DOCS_LLMS_TXT_URL,
    ),
    DocsSource(
        name="xls-standards",
        repo_url=XLS_STANDARDS_REPO_URL,
        path=Path(".cache/xrpl-standards"),
        url_base="https://github.com/XRPLF/XRPL-Standards/blob/master/",
        prefix_source_path=True,
        file_suffixes=MARKDOWN_SUFFIXES,
    ),
    DocsSource(
        name="xrpl4j",
        repo_url=XRPL4J_REPO_URL,
        path=Path(".cache/xrpl4j"),
        url_base="https://github.com/XRPLF/xrpl4j/blob/main/",
        prefix_source_path=True,
        file_suffixes=MARKDOWN_SUFFIXES,
    ),
    DocsSource(
        name="xrpl-go",
        repo_url=XRPL_GO_REPO_URL,
        path=Path(".cache/xrpl-go"),
        url_base="https://github.com/XRPLF/xrpl-go/blob/main/",
        prefix_source_path=True,
        file_suffixes=MARKDOWN_SUFFIXES,
    ),
    DocsSource(
        name="clio",
        repo_url=CLIO_REPO_URL,
        path=Path(".cache/clio"),
        url_base="https://github.com/XRPLF/clio/blob/develop/",
        prefix_source_path=True,
        file_suffixes=MARKDOWN_SUFFIXES,
    ),
    DocsSource(
        name="xahau-docs",
        repo_url=XAHAU_DOCS_REPO_URL,
        path=Path(".cache/xahau-docs"),
        url_base="https://docs.xahau.network/",
        prefix_source_path=True,
        file_suffixes=MARKDOWN_SUFFIXES,
    ),
    DocsSource(
        name="gemwallet-docs",
        repo_url=GEMWALLET_DOCS_REPO_URL,
        path=Path(".cache/gemwallet-website"),
        url_base="https://gemwallet.app/docs/",
        prefix_source_path=True,
        file_suffixes=frozenset({".md", ".mdx"}),
        include_parts=("docs",),
    ),
    DocsSource(
        name="ledger-docs",
        repo_url="",
        path=Path(".cache/ledger-docs"),
        url_base=LEDGER_DOCS_URL_BASE,
        prefix_source_path=True,
        file_suffixes=MARKDOWN_SUFFIXES,
        llms_txt_url=LEDGER_DOCS_LLMS_TXT_URL,
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


def ensure_web_docs(
    path: Path, llms_txt_url: str, base_url: str, update: bool = True
) -> Path:
    """Mirror a docs site that publishes an llms.txt index with .md page URLs."""
    if path.exists() and not update:
        return path
    if not path.exists() and not update:
        raise FileNotFoundError(f"Docs path does not exist: {path}")

    urls = parse_llms_txt(_fetch_text(llms_txt_url), base_url=base_url)
    if not urls:
        raise RuntimeError(f"No markdown page URLs found in {llms_txt_url}")

    for url in urls:
        target = local_path_for_doc_url(url, base_url=base_url, root=path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_fetch_text(url), encoding="utf-8")
    return path


def parse_llms_txt(text: str, base_url: str) -> list[str]:
    base = base_url.rstrip("/")
    urls: list[str] = []
    for match in re.finditer(r"\((https?://[^\s)]+\.md)\)", text):
        url = match.group(1)
        if url.startswith(base) and url not in urls:
            urls.append(url)
    return urls


def local_path_for_doc_url(url: str, base_url: str, root: Path) -> Path:
    relative = url[len(base_url.rstrip("/")) :].lstrip("/")
    return root / Path(relative)


def _fetch_text(url: str) -> str:
    # Some docs hosts reject urllib's default Python-urllib user agent.
    request = urllib.request.Request(url, headers={"User-Agent": "xrpl-docs-rag/0.1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


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
    # Directory parts starting with "." (e.g. .github, .claude, .agents) hold
    # repo tooling, not documentation.
    return any(
        part in SKIP_DIRS or part.startswith(".") for part in path.parts[:-1]
    )
