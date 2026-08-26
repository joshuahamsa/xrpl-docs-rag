from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Sequence

from xrpl_rag.code_map.models import CodeRecord, SourceFile


TEST_DIR_NAMES = {"test", "tests", "unittest", "unit_tests"}
TEST_NAME_TOKENS = ("_test", "test", "tests")


def build_relationships(
    records: Sequence[CodeRecord], source_files: Sequence[SourceFile] | None = None
) -> list[CodeRecord]:
    called_by = _build_called_by(records)
    related_tests = _build_related_tests(records, source_files or [])
    return [
        record.with_relationships(
            sorted(called_by.get(record.qualified_name, set())),
            sorted(related_tests.get(record.qualified_name, set())),
        )
        for record in records
    ]


def _build_called_by(
    records: Sequence[CodeRecord],
) -> defaultdict[str, set[str]]:
    symbol_index = _symbol_index(records)
    called_by: defaultdict[str, set[str]] = defaultdict(set)

    for caller in records:
        if caller.kind != "function":
            continue
        for call in caller.calls:
            candidates = symbol_index.get(call, set())
            if len(candidates) == 1:
                callee = next(iter(candidates))
                if callee != caller.qualified_name:
                    called_by[callee].add(caller.qualified_name)
    return called_by


def _symbol_index(records: Sequence[CodeRecord]) -> defaultdict[str, set[str]]:
    index: defaultdict[str, set[str]] = defaultdict(set)
    for record in records:
        if record.kind != "function":
            continue
        index[record.qualified_name].add(record.qualified_name)
        index[record.name].add(record.qualified_name)
        if record.class_name:
            index[f"{record.class_name}::{record.name}"].add(record.qualified_name)
    return index


def _build_related_tests(
    records: Sequence[CodeRecord], source_files: Sequence[SourceFile]
) -> defaultdict[str, set[str]]:
    test_files = [source_file for source_file in source_files if _is_test_file(source_file)]
    related_tests: defaultdict[str, set[str]] = defaultdict(set)

    for test_file in test_files:
        try:
            test_text = test_file.path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        test_name = Path(test_file.relative_path).name
        test_path = test_file.relative_path.lower()
        for record in records:
            if _test_matches_record(record, test_text, test_name, test_path):
                related_tests[record.qualified_name].add(test_file.relative_path)
    return related_tests


def _is_test_file(source_file: SourceFile) -> bool:
    path = Path(source_file.relative_path)
    parts = {part.lower() for part in path.parts}
    name = path.name.lower()
    return bool(parts & TEST_DIR_NAMES) or any(token in name for token in TEST_NAME_TOKENS)


def _test_matches_record(
    record: CodeRecord, test_text: str, test_name: str, test_path: str
) -> bool:
    source_path = Path(record.file)
    source_stem = source_path.stem
    source_parent = source_path.parent.name.lower()
    lowered_test_name = test_name.lower()

    if record.name and _contains_word(test_text, record.name):
        return True
    if record.class_name and (
        _contains_word(test_text, record.class_name)
        or record.class_name.lower() in lowered_test_name
    ):
        return True
    if source_stem and source_stem.lower() in lowered_test_name:
        return True
    if (
        source_parent
        and source_parent in test_path
        and (
            record.name.lower() in lowered_test_name
            or bool(record.class_name and record.class_name.lower() in lowered_test_name)
        )
    ):
        return True
    return False


def _contains_word(text: str, word: str) -> bool:
    return bool(word and re.search(rf"\b{re.escape(word)}\b", text))
