from __future__ import annotations

from typing import Sequence


class LocalEmbeddingFunction:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None

    def name(self) -> str:
        return self.model_name

    def __call__(self, input: Sequence[str]) -> list[list[float]]:
        return self.embed_documents(list(input))

    def embed_query(self, input: Sequence[str]) -> list[list[float]]:
        return self.embed_documents(list(input))

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        model = self._load_model()
        embeddings = model.encode(list(texts), normalize_embeddings=True)
        return [list(vector) for vector in embeddings]

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model
