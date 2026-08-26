from xrpl_rag.code_map.analyzers.cpp import CppAnalyzer
from xrpl_rag.code_map.models import SourceFile


def test_cpp_analyzer_extracts_class_method_free_function_and_calls(tmp_path):
    root = tmp_path / "repo"
    source_path = root / "src" / "Ledger.cpp"
    source_path.parent.mkdir(parents=True)
    source_path.write_text(
        """#include <memory>
#include "ripple/ledger/Ledger.h"

namespace ripple {

class Ledger {
public:
    void read();
};

// Reads the ledger from storage.
void Ledger::read()
{
    loadByIndex();
    helper();
}

int helper()
{
    return 1;
}

} // namespace ripple
""",
        encoding="utf-8",
    )
    source_file = SourceFile(root, source_path, "src/Ledger.cpp", "cpp")

    records = CppAnalyzer().analyze(source_file)

    class_record = next(record for record in records if record.kind == "class")
    method_record = next(
        record for record in records if record.qualified_name == "ripple::Ledger::read"
    )
    function_record = next(
        record for record in records if record.qualified_name == "ripple::helper"
    )

    assert class_record.name == "Ledger"
    assert class_record.namespace == "ripple"
    assert method_record.class_name == "Ledger"
    assert method_record.docstring == "Reads the ledger from storage."
    assert method_record.imports == ["memory", "ripple/ledger/Ledger.h"]
    assert method_record.calls == ["loadByIndex", "helper"]
    assert "void Ledger::read()" in method_record.signature
    assert method_record.line_start == 12
    assert function_record.calls == []


def test_cpp_analyzer_truncates_code_without_losing_record_extent(tmp_path):
    root = tmp_path / "repo"
    source_path = root / "Long.cpp"
    source_path.parent.mkdir(parents=True)
    source_path.write_text(
        "void longFunction()\n{\n"
        + "\n".join(f"    call{i}();" for i in range(20))
        + "\n}\n",
        encoding="utf-8",
    )
    source_file = SourceFile(root, source_path, "Long.cpp", "cpp")

    record = CppAnalyzer().analyze(source_file, max_code_chars=80)[0]

    assert record.qualified_name == "longFunction"
    assert record.line_end == 23
    assert len(record.code) <= 80
    assert record.code.endswith("[truncated]")
