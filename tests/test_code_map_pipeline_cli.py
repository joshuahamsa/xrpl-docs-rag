from typer.testing import CliRunner

from xrpl_rag.cli import app
from xrpl_rag.code_map.pipeline import map_codebase


def make_repo(tmp_path):
    root = tmp_path / "repo"
    source = root / "src" / "Ledger.cpp"
    test = root / "src" / "test" / "Ledger_test.cpp"
    source.parent.mkdir(parents=True)
    test.parent.mkdir(parents=True)
    source.write_text(
        """#include "Ledger.h"
namespace ripple {
void helper() {}
void read()
{
    helper();
}
}
""",
        encoding="utf-8",
    )
    test.write_text("void test_read() { read(); }", encoding="utf-8")
    return root


def test_map_codebase_writes_both_outputs(tmp_path):
    root = make_repo(tmp_path)
    out_dir = tmp_path / "out"

    result = map_codebase(root, out_dir)

    assert len(result.records) == 3
    assert result.outputs["jsonl"] == out_dir / "records.jsonl"
    assert result.outputs["markdown"] == out_dir / "markdown"
    assert (out_dir / "records.jsonl").exists()
    assert (out_dir / "markdown" / "src" / "Ledger.cpp.md").exists()
    read_record = next(record for record in result.records if record.qualified_name == "ripple::read")
    assert read_record.called_by == ["test_read"]
    assert read_record.related_tests == ["src/test/Ledger_test.cpp"]


def test_map_codebase_errors_when_root_missing(tmp_path):
    missing = tmp_path / "missing"

    try:
        map_codebase(missing, tmp_path / "out")
    except FileNotFoundError as exc:
        assert "Codebase path does not exist" in str(exc)
    else:
        raise AssertionError("Expected FileNotFoundError")


def test_cli_map_code_command(tmp_path):
    root = make_repo(tmp_path)
    out_dir = tmp_path / "out"
    runner = CliRunner()

    result = runner.invoke(
        app, ["map-code", str(root), "--out", str(out_dir), "--format", "jsonl"]
    )

    assert result.exit_code == 0
    assert "Mapped" in result.output
    assert (out_dir / "records.jsonl").exists()


def test_map_codebase_reports_progress_and_throttles(tmp_path, monkeypatch):
    root = make_repo(tmp_path)
    out_dir = tmp_path / "out"
    progress_messages = []
    sleeps = []

    monkeypatch.setattr("xrpl_rag.code_map.pipeline.time.sleep", sleeps.append)

    map_codebase(
        root,
        out_dir,
        output_format="jsonl",
        progress_callback=progress_messages.append,
        progress_every=1,
        throttle_ms=7,
    )

    assert progress_messages == [
        "Scanning source files...",
        "Found 2 supported source files.",
        "Analyzed 1/2 files, records=2.",
        "Analyzed 2/2 files, records=3.",
        "Building relationships...",
        "Writing outputs...",
    ]
    assert sleeps == [0.007, 0.007]


def test_cli_map_code_prints_progress_to_stderr(tmp_path):
    root = make_repo(tmp_path)
    out_dir = tmp_path / "out"
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "map-code",
            str(root),
            "--out",
            str(out_dir),
            "--format",
            "jsonl",
            "--progress-every",
            "1",
            "--throttle-ms",
            "0",
        ],
    )

    assert result.exit_code == 0
    assert "Mapped 3 records from 2 files." in result.output
    assert "Scanning source files..." in result.stderr
    assert "Analyzed 2/2 files, records=3." in result.stderr
