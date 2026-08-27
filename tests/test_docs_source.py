import subprocess

import pytest

from xrpl_rag.docs_source import (
    DEFAULT_DOC_SOURCES,
    ensure_docs_repo,
    iter_document_files,
    iter_markdown_files,
)


def test_ensure_docs_repo_uses_existing_local_path_without_git(tmp_path):
    docs_path = tmp_path / "xrpl-dev-portal"
    docs_path.mkdir()

    assert ensure_docs_repo(docs_path, update=False) == docs_path


def test_ensure_docs_repo_fails_for_missing_local_path_when_clone_disabled(tmp_path):
    with pytest.raises(FileNotFoundError, match="Docs path does not exist"):
        ensure_docs_repo(tmp_path / "missing", update=False)


def test_iter_markdown_files_filters_common_non_docs_dirs(tmp_path):
    docs_path = tmp_path / "repo"
    keep = docs_path / "docs" / "concepts" / "accounts.md"
    skip = docs_path / "node_modules" / "package" / "README.md"
    keep.parent.mkdir(parents=True)
    skip.parent.mkdir(parents=True)
    keep.write_text("# Accounts", encoding="utf-8")
    skip.write_text("# Dependency", encoding="utf-8")

    assert list(iter_markdown_files(docs_path)) == [keep]


def test_default_doc_sources_include_xrpl_python_and_javascript_libraries():
    assert [source.name for source in DEFAULT_DOC_SOURCES] == [
        "xrpl-docs",
        "xrpl-py",
        "xrpl-js",
        "xaman-docs",
        "joey-docs",
    ]
    assert [source.repo_url for source in DEFAULT_DOC_SOURCES] == [
        "https://github.com/XRPLF/xrpl-dev-portal.git",
        "https://github.com/XRPLF/xrpl-py.git",
        "https://github.com/XRPLF/xrpl.js.git",
        "https://github.com/XRPL-Labs/Developer-Help-Center.git",
        "",
    ]
    assert [source.path.name for source in DEFAULT_DOC_SOURCES] == [
        "xrpl-dev-portal",
        "xrpl-py",
        "xrpl.js",
        "xaman-docs",
        "joey-docs",
    ]
    xrpl_py = DEFAULT_DOC_SOURCES[1]
    assert ".py" in xrpl_py.file_suffixes
    assert xrpl_py.include_parts == ("docs", "xrpl")
    assert xrpl_py.source_url_base == "https://github.com/XRPLF/xrpl-py/blob/main/"


def test_iter_document_files_includes_rst_and_html_but_skips_assets(tmp_path):
    docs_path = tmp_path / "repo"
    markdown = docs_path / "docs" / "concepts" / "accounts.md"
    rst = docs_path / "docs" / "source" / "xrpl.transaction.rst"
    html = docs_path / "docs" / "classes" / "Client.html"
    asset = docs_path / "docs" / "assets" / "style.css"
    node_module = docs_path / "node_modules" / "package" / "README.md"
    for path in [markdown, rst, html, asset, node_module]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("docs", encoding="utf-8")

    assert list(iter_document_files(docs_path)) == [html, markdown, rst]


def test_iter_document_files_can_limit_to_source_roots(tmp_path):
    docs_path = tmp_path / "repo"
    keep = docs_path / "xrpl" / "transaction" / "main.py"
    skip = docs_path / "tests" / "test_transaction.py"
    for path in [keep, skip]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("docs", encoding="utf-8")

    assert list(iter_document_files(docs_path, {".py"}, include_parts=("xrpl",))) == [
        keep
    ]


def test_ensure_docs_repo_clones_missing_path(monkeypatch, tmp_path):
    calls = []

    def fake_run(command, check):
        calls.append((command, check))

    monkeypatch.setattr(subprocess, "run", fake_run)

    path = ensure_docs_repo(tmp_path / "repo", update=True, repo_url="https://example.test/repo.git")

    assert path == tmp_path / "repo"
    assert calls == [
        (
            [
                "git",
                "clone",
                "--depth",
                "1",
                "https://example.test/repo.git",
                str(tmp_path / "repo"),
            ],
            True,
        )
    ]
