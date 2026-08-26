from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_DOCS_PATH = Path(".cache/xrpl-dev-portal")
DEFAULT_DB_PATH = Path(".rag/chroma")
DEFAULT_COLLECTION = "xrpl_docs"
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


@dataclass(frozen=True)
class RagConfig:
    docs_path: Path = DEFAULT_DOCS_PATH
    db_path: Path = DEFAULT_DB_PATH
    collection_name: str = DEFAULT_COLLECTION
    embedding_model: str = DEFAULT_EMBEDDING_MODEL

    @classmethod
    def from_env(cls) -> "RagConfig":
        return cls(
            docs_path=Path(os.environ.get("XRPL_RAG_DOCS_PATH", DEFAULT_DOCS_PATH)),
            db_path=Path(os.environ.get("XRPL_RAG_DB_PATH", DEFAULT_DB_PATH)),
            collection_name=os.environ.get("XRPL_RAG_COLLECTION", DEFAULT_COLLECTION),
            embedding_model=os.environ.get(
                "XRPL_RAG_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL
            ),
        )

    def resolve(self, base_path: Path | None = None) -> "RagConfig":
        base = base_path or Path.cwd()
        return RagConfig(
            docs_path=_resolve_path(self.docs_path, base),
            db_path=_resolve_path(self.db_path, base),
            collection_name=self.collection_name,
            embedding_model=self.embedding_model,
        )


def _resolve_path(path: Path, base_path: Path) -> Path:
    return path if path.is_absolute() else base_path / path
