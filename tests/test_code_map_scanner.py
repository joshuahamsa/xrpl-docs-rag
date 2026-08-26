from xrpl_rag.code_map.models import CodeRecord
from xrpl_rag.code_map.scanner import scan_source_files


def test_scan_source_files_detects_cpp_and_skips_defaults(tmp_path):
    root = tmp_path / "repo"
    (root / "src").mkdir(parents=True)
    (root / "src" / "Ledger.cpp").write_text("int main() { return 0; }", encoding="utf-8")
    (root / "src" / "Ledger.h").write_text("#pragma once\n", encoding="utf-8")
    (root / "build").mkdir()
    (root / "build" / "Generated.cpp").write_text("void generated() {}", encoding="utf-8")
    (root / ".rag").mkdir()
    (root / ".rag" / "records.cpp").write_text("void cached() {}", encoding="utf-8")

    files = scan_source_files(root)

    assert [file.relative_path for file in files] == ["src/Ledger.cpp", "src/Ledger.h"]
    assert {file.language for file in files} == {"cpp"}


def test_scan_source_files_applies_include_and_exclude_globs(tmp_path):
    root = tmp_path / "repo"
    (root / "src").mkdir(parents=True)
    (root / "test").mkdir()
    (root / "src" / "A.cpp").write_text("void a() {}", encoding="utf-8")
    (root / "src" / "B.cpp").write_text("void b() {}", encoding="utf-8")
    (root / "test" / "A_test.cpp").write_text("void test_a() {}", encoding="utf-8")

    files = scan_source_files(root, include=["src/*.cpp"], exclude=["**/B.cpp"])

    assert [file.relative_path for file in files] == ["src/A.cpp"]


def test_code_record_to_dict_uses_json_field_names():
    record = CodeRecord(
        record_id="abc",
        kind="function",
        language="cpp",
        name="read",
        qualified_name="ripple::Ledger::read",
        file="src/Ledger.cpp",
        line_start=3,
        line_end=8,
        class_name="Ledger",
        namespace="ripple",
        signature="void Ledger::read()",
        docstring="Reads a ledger.",
        imports=["ripple/Ledger.h"],
        code="void Ledger::read() {}",
        calls=["load"],
    )

    assert record.to_dict()["class"] == "Ledger"
    assert record.to_dict()["called_by"] == []
    assert "class_name" not in record.to_dict()
