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


def _chunk(chunk_id, text="text"):
    return DocumentChunk(
        chunk_id=chunk_id,
        source_path="docs/test.md",
        title="Test",
        heading_path="Test",
        url="https://xrpl.org/docs/test",
        text=text,
        embedding_text=text,
    )


class FakeDiffCollection:
    def __init__(self, existing_ids):
        self.ids = set(existing_ids)
        self.upserted = []
        self.deleted = []

    def count(self):
        return len(self.ids)

    def get(self, limit, offset, include):
        return {"ids": sorted(self.ids)[offset : offset + limit]}

    def upsert(self, ids, documents, metadatas):
        self.upserted.extend(ids)
        self.ids.update(ids)

    def delete(self, ids):
        self.deleted.extend(ids)
        self.ids.difference_update(ids)


def test_sync_chunks_only_embeds_new_and_deletes_stale():
    collection = FakeDiffCollection({"keep", "stale"})
    store = object.__new__(VectorStore)
    store.collection = collection

    added, removed, unchanged = store.sync_chunks([_chunk("keep"), _chunk("new")])

    assert (added, removed, unchanged) == (1, 1, 1)
    assert collection.upserted == ["new"]
    assert collection.deleted == ["stale"]
    assert collection.ids == {"keep", "new"}


def test_sync_chunks_keeps_stale_when_deletion_disabled():
    collection = FakeDiffCollection({"other-source"})
    store = object.__new__(VectorStore)
    store.collection = collection

    added, removed, unchanged = store.sync_chunks(
        [_chunk("new")], delete_stale=False
    )

    assert (added, removed, unchanged) == (1, 0, 0)
    assert collection.deleted == []
    assert collection.ids == {"other-source", "new"}
