from xrpl_rag.embeddings import LocalEmbeddingFunction


def test_local_embedding_function_has_chroma_name_without_loading_model():
    embedding = LocalEmbeddingFunction("sentence-transformers/all-MiniLM-L6-v2")

    assert embedding.name() == "sentence-transformers/all-MiniLM-L6-v2"
    assert embedding._model is None


def test_local_embedding_function_supports_chroma_query_protocol(monkeypatch):
    class FakeModel:
        def encode(self, texts, normalize_embeddings):
            assert texts == ["hello"]
            assert normalize_embeddings is True
            return [[1.0, 0.0]]

    embedding = LocalEmbeddingFunction("fake")
    monkeypatch.setattr(embedding, "_load_model", lambda: FakeModel())

    assert embedding.embed_query(input=["hello"]) == [[1.0, 0.0]]
