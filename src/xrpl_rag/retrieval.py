from __future__ import annotations

from typing import Any

from xrpl_rag.config import RagConfig
from xrpl_rag.formatting import SearchResult
from xrpl_rag.store import VectorStore


def retrieve(query: str, config: RagConfig, top_k: int = 5) -> list[SearchResult]:
    store = VectorStore(config)
    return results_from_chroma_query(store.query(query, top_k))


def results_from_chroma_query(response: dict[str, Any]) -> list[SearchResult]:
    documents = _first(response.get("documents", []))
    metadatas = _first(response.get("metadatas", []))
    distances = _first(response.get("distances", []))

    results: list[SearchResult] = []
    for index, metadata in enumerate(metadatas):
        document = documents[index] if index < len(documents) else ""
        distance = distances[index] if index < len(distances) else 1.0
        text = str(metadata.get("text") or document)
        results.append(
            SearchResult(
                title=str(metadata.get("title", "Untitled")),
                heading_path=str(metadata.get("heading_path", "")),
                url=str(metadata.get("url", "")),
                source_path=str(metadata.get("source_path", "")),
                text=text,
                score=_similarity_score(distance),
            )
        )
    return results


def _first(value):
    if not value:
        return []
    return value[0]


def _similarity_score(distance: float) -> float:
    return 1.0 / (1.0 + float(distance))
