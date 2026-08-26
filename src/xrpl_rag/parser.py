from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


@dataclass(frozen=True)
class ParsedPage:
    source_path: str
    title: str
    url: str
    text: str
    headings: list[str]


def parse_markdown_file(path: Path, repo_root: Path) -> ParsedPage:
    raw = path.read_text(encoding="utf-8")
    metadata, body = _split_frontmatter(raw)
    text = _clean_mdx_lines(body)
    headings = _extract_headings(text)
    source_path = path.relative_to(repo_root).as_posix()
    title = _title_for_page(metadata, headings, path)

    return ParsedPage(
        source_path=source_path,
        title=title,
        url=derive_docs_url(source_path),
        text=text.strip(),
        headings=headings,
    )


def derive_docs_url(source_path: str) -> str:
    path = source_path
    if path.startswith("docs/"):
        path = path.removeprefix("docs/")
    path = re.sub(r"\.mdx?$", "", path)
    path = re.sub(r"/index$", "", path)
    return f"https://xrpl.org/docs/{path.strip('/')}"


def _split_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    match = FRONTMATTER_RE.match(raw)
    if not match:
        return {}, raw

    parsed = yaml.safe_load(match.group(1)) or {}
    if not isinstance(parsed, dict):
        parsed = {}
    return parsed, raw[match.end() :]


def _clean_mdx_lines(text: str) -> str:
    cleaned: list[str] = []
    in_code_block = False

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            cleaned.append(line)
            continue
        if not in_code_block and _is_mdx_only_line(stripped):
            continue
        cleaned.append(line)

    return "\n".join(cleaned)


def _is_mdx_only_line(stripped: str) -> bool:
    if not stripped:
        return False
    if stripped.startswith(("import ", "export ")):
        return True
    return bool(re.fullmatch(r"</?[A-Z][A-Za-z0-9_.:-]*(\s+[^>]*)?/?>", stripped))


def _extract_headings(text: str) -> list[str]:
    headings: list[str] = []
    in_code_block = False

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        match = HEADING_RE.match(stripped)
        if match:
            headings.append(_clean_heading(match.group(2)))
    return headings


def _title_for_page(metadata: dict[str, Any], headings: list[str], path: Path) -> str:
    title = metadata.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    if headings:
        return headings[0]
    return path.stem


def _clean_heading(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().strip("#")).strip()
