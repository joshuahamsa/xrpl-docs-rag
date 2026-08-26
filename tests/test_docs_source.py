import subprocess

import pytest

from xrpl_rag.docs_source import ensure_docs_repo, iter_markdown_files


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
