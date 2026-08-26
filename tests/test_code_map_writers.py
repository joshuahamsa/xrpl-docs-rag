import json

from xrpl_rag.code_map.models import CodeRecord
from xrpl_rag.code_map.writers import write_jsonl, write_markdown, write_outputs


def sample_record():
    return CodeRecord(
        record_id="abc",
        kind="function",
        language="cpp",
        name="read",
        qualified_name="ripple::Ledger::read",
        file="src/ripple/ledger/Ledger.cpp",
        line_start=12,
        line_end=16,
        class_name="Ledger",
        namespace="ripple",
        signature="void Ledger::read()",
        docstring="Reads the ledger.",
        imports=["ripple/ledger/Ledger.h"],
        code="void Ledger::read() {}",
        calls=["helper"],
        called_by=["ripple::main"],
        related_tests=["src/test/ledger/Ledger_test.cpp"],
    )


def test_write_jsonl_writes_one_record_per_line(tmp_path):
    output_path = tmp_path / "records.jsonl"

    count = write_jsonl([sample_record()], output_path)

    assert count == 1
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["qualified_name"] == "ripple::Ledger::read"
    assert payload["class"] == "Ledger"
    assert "Kind: function" in payload["embedding_text"]


def test_write_markdown_groups_records_by_source_file(tmp_path):
    count = write_markdown([sample_record()], tmp_path / "markdown")

    output = tmp_path / "markdown" / "src" / "ripple" / "ledger" / "Ledger.cpp.md"
    assert count == 1
    text = output.read_text(encoding="utf-8")
    assert "## Function: ripple::Ledger::read" in text
    assert "File: src/ripple/ledger/Ledger.cpp:12" in text
    assert "- ripple/ledger/Ledger.h" in text
    assert "```cpp" in text


def test_write_outputs_respects_format(tmp_path):
    outputs = write_outputs([sample_record()], tmp_path, "jsonl")

    assert outputs == {"jsonl": tmp_path / "records.jsonl"}
    assert (tmp_path / "records.jsonl").exists()
    assert not (tmp_path / "markdown").exists()
