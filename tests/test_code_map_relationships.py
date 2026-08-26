from xrpl_rag.code_map.models import CodeRecord, SourceFile
from xrpl_rag.code_map.relationships import build_relationships


def make_record(name, qualified_name, file, calls=None, class_name=""):
    return CodeRecord(
        record_id=qualified_name,
        kind="function",
        language="cpp",
        name=name,
        qualified_name=qualified_name,
        file=file,
        line_start=1,
        line_end=3,
        class_name=class_name,
        code=f"void {name}() {{}}",
        calls=calls or [],
    )


def test_build_relationships_derives_called_by_for_unambiguous_calls():
    read = make_record(
        "read", "ripple::Ledger::read", "src/ripple/ledger/Ledger.cpp", ["helper"]
    )
    helper = make_record("helper", "ripple::helper", "src/ripple/ledger/Helpers.cpp")
    other = make_record("main", "ripple::main", "src/main.cpp", ["read"])

    records = build_relationships([read, helper, other])

    by_name = {record.qualified_name: record for record in records}
    assert by_name["ripple::helper"].called_by == ["ripple::Ledger::read"]
    assert by_name["ripple::Ledger::read"].called_by == ["ripple::main"]


def test_build_relationships_ignores_ambiguous_unqualified_calls():
    caller = make_record("caller", "caller", "caller.cpp", ["shared"])
    first = make_record("shared", "a::shared", "a.cpp")
    second = make_record("shared", "b::shared", "b.cpp")

    records = build_relationships([caller, first, second])

    assert all(record.called_by == [] for record in records)


def test_build_relationships_links_related_tests_by_path_and_symbol(tmp_path):
    root = tmp_path / "repo"
    source = root / "src" / "ripple" / "ledger" / "Ledger.cpp"
    test = root / "src" / "test" / "ledger" / "Ledger_test.cpp"
    source.parent.mkdir(parents=True)
    test.parent.mkdir(parents=True)
    source.write_text("void read() {}", encoding="utf-8")
    test.write_text("void test_read() { read(); }", encoding="utf-8")
    record = make_record(
        "read", "ripple::Ledger::read", "src/ripple/ledger/Ledger.cpp", class_name="Ledger"
    )
    source_file = SourceFile(root, source, "src/ripple/ledger/Ledger.cpp", "cpp")
    test_file = SourceFile(root, test, "src/test/ledger/Ledger_test.cpp", "cpp")

    records = build_relationships([record], [source_file, test_file])

    assert records[0].related_tests == ["src/test/ledger/Ledger_test.cpp"]
