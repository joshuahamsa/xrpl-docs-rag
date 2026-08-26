from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from xrpl_rag.parser import HEADING_RE, ParsedPage


@dataclass(frozen=True)
class DocumentChunk:
    chunk_id: str
    source_path: str
    title: str
    heading_path: str
    url: str
    text: str
    embedding_text: str

    def metadata(self) -> dict[str, str]:
        return {
            "chunk_id": self.chunk_id,
            "source_path": self.source_path,
            "title": self.title,
            "heading_path": self.heading_path,
            "url": self.url,
            "text": self.text,
        }


@dataclass(frozen=True)
class _Section:
    heading_path: str
    text: str


def chunk_page(
    page: ParsedPage, max_words: int = 900, overlap_words: int = 120
) -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []
    for section in _sections_for_page(page):
        for part_index, text in enumerate(
            _split_words(section.text, max_words=max_words, overlap_words=overlap_words)
        ):
            chunks.append(_make_chunk(page, section.heading_path, text, part_index))
    return chunks


def _sections_for_page(page: ParsedPage) -> list[_Section]:
    sections: list[_Section] = []
    heading_stack: list[tuple[int, str]] = []
    current_lines: list[str] = []
    current_heading = page.title
    in_code_block = False

    def flush() -> None:
        text = "\n".join(current_lines).strip()
        if text:
            sections.append(_Section(current_heading, text))
        current_lines.clear()

    for line in page.text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            current_lines.append(line)
            continue

        match = None if in_code_block else HEADING_RE.match(stripped)
        if match:
            flush()
            level = len(match.group(1))
            heading = _clean_heading(match.group(2))
            heading_stack[:] = [(lvl, text) for lvl, text in heading_stack if lvl < level]
            heading_stack.append((level, heading))
            current_heading = " > ".join(text for _, text in heading_stack)
            continue

        current_lines.append(line)

    flush()
    if sections:
        return sections
    return [_Section(page.title, page.text.strip())] if page.text.strip() else []


def _split_words(text: str, max_words: int, overlap_words: int) -> list[str]:
    words = text.split()
    if len(words) <= max_words:
        return [text.strip()]

    chunks: list[str] = []
    start = 0
    step = max(1, max_words - overlap_words)
    while start < len(words):
        end = min(start + max_words, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += step
    return chunks


def _make_chunk(
    page: ParsedPage, heading_path: str, text: str, part_index: int
) -> DocumentChunk:
    embedding_text = f"Title: {page.title}\nHeading: {heading_path}\n\n{text}"
    chunk_id = _chunk_id(page.source_path, heading_path, part_index, text)
    return DocumentChunk(
        chunk_id=chunk_id,
        source_path=page.source_path,
        title=page.title,
        heading_path=heading_path,
        url=page.url,
        text=text,
        embedding_text=embedding_text,
    )


def _chunk_id(source_path: str, heading_path: str, part_index: int, text: str) -> str:
    value = f"{source_path}\0{heading_path}\0{part_index}\0{text}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _clean_heading(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().strip("#")).strip()
