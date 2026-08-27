from typer.testing import CliRunner

from xrpl_rag.cli import app
from xrpl_rag.docs_source import DEFAULT_DOC_SOURCES


class FakeStore:
    upserted_chunks = []

    def __init__(self, config):
        self.config = config

    def upsert_chunks(self, chunks):
        self.__class__.upserted_chunks = list(chunks)


def test_ingest_indexes_all_default_doc_sources(monkeypatch, tmp_path):
    roots = {}
    for source in DEFAULT_DOC_SOURCES:
        root = tmp_path / source.path.name
        roots[source.name] = root
        if source.name == "xrpl-docs":
            page = root / "docs" / "concepts" / "accounts.md"
            page.parent.mkdir(parents=True)
            page.write_text("# Accounts\n\nXRPL account docs.", encoding="utf-8")
        elif source.name == "xaman-docs":
            page = root / "js-ts-sdk" / "sdk.md"
            page.parent.mkdir(parents=True)
            page.write_text("# Xaman SDK\n\nXaman developer docs.", encoding="utf-8")
        elif source.name == "joey-docs":
            page = root / "overview" / "getting-started.md"
            page.parent.mkdir(parents=True)
            page.write_text("# Getting Started\n\nJoey Wallet docs.", encoding="utf-8")
        elif source.name == "xrpl-py":
            page = root / "docs" / "source" / "xrpl.transaction.rst"
            page.parent.mkdir(parents=True)
            page.write_text(
                "Transaction Methods\n===================\n\nPython transaction docs.",
                encoding="utf-8",
            )
        else:
            page = root / "docs" / "classes" / "Client.html"
            page.parent.mkdir(parents=True)
            page.write_text(
                "<html><body><h1>Class Client</h1>"
                "<p>JavaScript client docs.</p></body></html>",
                encoding="utf-8",
            )

    def fake_ensure(path, update=True, repo_url=None):
        for source in DEFAULT_DOC_SOURCES:
            if repo_url and repo_url == source.repo_url:
                return roots[source.name]
        raise AssertionError(f"Unexpected docs source: {path}")

    def fake_ensure_web(path, llms_txt_url, base_url, update=True):
        return roots["joey-docs"]

    monkeypatch.setattr("xrpl_rag.cli.ensure_docs_repo", fake_ensure)
    monkeypatch.setattr("xrpl_rag.cli.ensure_web_docs", fake_ensure_web)
    monkeypatch.setattr("xrpl_rag.cli.VectorStore", FakeStore)

    result = CliRunner().invoke(app, ["ingest"])

    assert result.exit_code == 0
    assert "Indexed 5 chunks from 5 files across 5 sources." in result.output
    assert {chunk.source_path for chunk in FakeStore.upserted_chunks} == {
        "docs/concepts/accounts.md",
        "xrpl-py:docs/source/xrpl.transaction.rst",
        "xrpl-js:docs/classes/Client.html",
        "xaman-docs:js-ts-sdk/sdk.md",
        "joey-docs:overview/getting-started.md",
    }
