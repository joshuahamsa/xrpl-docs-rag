from xrpl_rag.config import RagConfig


def test_config_resolves_relative_paths(tmp_path, monkeypatch):
    monkeypatch.delenv("XRPL_RAG_DOCS_PATH", raising=False)
    monkeypatch.delenv("XRPL_RAG_DB_PATH", raising=False)
    monkeypatch.delenv("XRPL_RAG_COLLECTION", raising=False)
    monkeypatch.delenv("XRPL_RAG_EMBEDDING_MODEL", raising=False)

    config = RagConfig.from_env().resolve(tmp_path)

    assert config.docs_path == tmp_path / ".cache" / "xrpl-dev-portal"
    assert config.db_path == tmp_path / ".rag" / "chroma"
    assert config.collection_name == "xrpl_docs"
    assert config.embedding_model == "sentence-transformers/all-MiniLM-L6-v2"


def test_config_uses_environment_overrides(tmp_path, monkeypatch):
    docs_path = tmp_path / "docs"
    db_path = tmp_path / "db"
    monkeypatch.setenv("XRPL_RAG_DOCS_PATH", str(docs_path))
    monkeypatch.setenv("XRPL_RAG_DB_PATH", str(db_path))
    monkeypatch.setenv("XRPL_RAG_COLLECTION", "custom")
    monkeypatch.setenv("XRPL_RAG_EMBEDDING_MODEL", "local-model")

    config = RagConfig.from_env().resolve(tmp_path)

    assert config.docs_path == docs_path
    assert config.db_path == db_path
    assert config.collection_name == "custom"
    assert config.embedding_model == "local-model"
