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
