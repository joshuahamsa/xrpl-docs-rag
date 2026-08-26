from __future__ import annotations

from typing import Protocol

from xrpl_rag.code_map.models import CodeRecord, SourceFile


class Analyzer(Protocol):
    language: str

    def analyze(
        self, source_file: SourceFile, max_code_chars: int = 12_000
    ) -> list[CodeRecord]:
        raise NotImplementedError
