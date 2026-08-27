from __future__ import annotations

from typing import Sequence

from xrpl_rag.chunker import DocumentChunk
from xrpl_rag.config import RagConfig
from xrpl_rag.embeddings import LocalEmbeddingFunction


DEFAULT_UPSERT_BATCH_SIZE = 5_000


class VectorStore:
    def __init__(self, config: RagConfig, embedding_function=None):
        self.config = config
        self.embedding_function = embedding_function or LocalEmbeddingFunction(
            config.embedding_model
        )
        self.collection = self._collection()

    def upsert_chunks(
        self, chunks: Sequence[DocumentChunk], batch_size: int = DEFAULT_UPSERT_BATCH_SIZE
    ) -> None:
        if not chunks:
            return
        for start in range(0, len(chunks), batch_size):
            batch = chunks[start : start + batch_size]
            self.collection.upsert(
                ids=[chunk.chunk_id for chunk in batch],
                documents=[chunk.embedding_text for chunk in batch],
                metadatas=[chunk.metadata() for chunk in batch],
            )

    def sync_chunks(
        self,
        chunks: Sequence[DocumentChunk],
        batch_size: int = DEFAULT_UPSERT_BATCH_SIZE,
        delete_stale: bool = True,
    ) -> tuple[int, int, int]:
        """Diff chunks against the collection by chunk_id and only embed new ones.

        Chunk IDs hash the chunk content, so an unchanged chunk keeps its ID
        across ingests and needs no re-embedding. Returns
        (added, removed, unchanged) counts.
        """
        existing = self._existing_ids(batch_size)
        desired = {chunk.chunk_id: chunk for chunk in chunks}

        new_chunks = [
            chunk for chunk_id, chunk in desired.items() if chunk_id not in existing
        ]
        stale_ids = sorted(existing - desired.keys()) if delete_stale else []

        self.upsert_chunks(new_chunks, batch_size=batch_size)
        for start in range(0, len(stale_ids), batch_size):
            self.collection.delete(ids=stale_ids[start : start + batch_size])

        return len(new_chunks), len(stale_ids), len(desired) - len(new_chunks)

    def _existing_ids(self, batch_size: int) -> set[str]:
        ids: set[str] = set()
        count = self.collection.count()
        for offset in range(0, count, batch_size):
            result = self.collection.get(
                limit=batch_size, offset=offset, include=[]
            )
            ids.update(result["ids"])
        return ids

    def query(self, query: str, top_k: int):
        return self.collection.query(query_texts=[query], n_results=top_k)

    def _collection(self):
        import chromadb

        self.config.db_path.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(self.config.db_path))
        return client.get_or_create_collection(
            name=self.config.collection_name,
            embedding_function=self.embedding_function,
        )
