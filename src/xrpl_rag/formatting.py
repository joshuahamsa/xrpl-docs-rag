from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class SearchResult:
    title: str
    heading_path: str
    url: str
    source_path: str
    text: str
    score: float


def format_search_results(results: Sequence[SearchResult]) -> str:
    if not results:
        return "No XRPL docs matches found."

    blocks: list[str] = []
    for index, result in enumerate(results, start=1):
        blocks.append(
            "\n".join(
                [
                    f"[{index}] {result.title}",
                    f"Heading: {result.heading_path}",
                    f"URL: {result.url}",
                    f"Source: {result.source_path}",
                    f"Score: {result.score:.4f}",
                    f"Excerpt: {_compact(result.text)}",
                ]
            )
        )
    return "\n\n".join(blocks)


def format_context(question: str, results: Sequence[SearchResult]) -> str:
    lines = [f"Question: {question}", "", "Relevant XRPL docs:"]
    if not results:
        lines.append("No relevant XRPL docs were found.")
        return "\n".join(lines)

    for index, result in enumerate(results, start=1):
        lines.extend(
            [
                f"[{index}] {result.title}",
                f"Heading: {result.heading_path}",
                f"URL: {result.url}",
                f"Excerpt: {_compact(result.text)}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def _compact(text: str) -> str:
    return " ".join(text.split())
