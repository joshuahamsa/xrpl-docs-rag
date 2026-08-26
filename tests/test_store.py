from xrpl_rag.chunker import DocumentChunk
from xrpl_rag.store import VectorStore


def test_vector_store_batches_upserts():
    class FakeCollection:
        def __init__(self):
            self.calls = []

        def upsert(self, ids, documents, metadatas):
            self.calls.append((ids, documents, metadatas))

    collection = FakeCollection()
    store = object.__new__(VectorStore)
    store.collection = collection
    chunks = [
        DocumentChunk(
            chunk_id=f"chunk-{index}",
            source_path="docs/test.md",
            title="Test",
            heading_path="Test",
            url="https://xrpl.org/docs/test",
            text=f"text {index}",
            embedding_text=f"embedding {index}",
        )
        for index in range(5)
    ]

    store.upsert_chunks(chunks, batch_size=2)

    assert [len(call[0]) for call in collection.calls] == [2, 2, 1]
    assert collection.calls[0][0] == ["chunk-0", "chunk-1"]
    assert collection.calls[-1][0] == ["chunk-4"]
