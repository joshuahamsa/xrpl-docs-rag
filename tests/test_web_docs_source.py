from xrpl_rag.docs_source import (
    DEFAULT_DOC_SOURCES,
    ensure_web_docs,
    local_path_for_doc_url,
    parse_llms_txt,
)


LLMS_TXT = """\
# Joey Wallet

## Developer Docs

- [Welcome](https://docs.joeywallet.xyz/welcome-to-joey-wallet.md)
- [Getting Started](https://docs.joeywallet.xyz/overview/getting-started.md)
- [Connect](https://docs.joeywallet.xyz/integration/actions/connect.md): connect action
- [External](https://example.com/other.md)
- [Not markdown](https://docs.joeywallet.xyz/overview/page)
"""


def test_parse_llms_txt_extracts_same_site_markdown_urls():
    urls = parse_llms_txt(LLMS_TXT, base_url="https://docs.joeywallet.xyz/")
    assert urls == [
        "https://docs.joeywallet.xyz/welcome-to-joey-wallet.md",
        "https://docs.joeywallet.xyz/overview/getting-started.md",
        "https://docs.joeywallet.xyz/integration/actions/connect.md",
    ]


def test_local_path_for_doc_url_mirrors_site_structure(tmp_path):
    path = local_path_for_doc_url(
        "https://docs.joeywallet.xyz/integration/actions/connect.md",
        base_url="https://docs.joeywallet.xyz/",
        root=tmp_path,
    )
    assert path == tmp_path / "integration" / "actions" / "connect.md"


def test_ensure_web_docs_downloads_pages(monkeypatch, tmp_path):
    fetched = []

    def fake_fetch(url):
        fetched.append(url)
        if url.endswith("llms.txt"):
            return LLMS_TXT
        return f"# Page\n\nContent of {url}"

    monkeypatch.setattr("xrpl_rag.docs_source._fetch_text", fake_fetch)

    root = tmp_path / "joey-docs"
    result = ensure_web_docs(
        root,
        llms_txt_url="https://docs.joeywallet.xyz/llms.txt",
        base_url="https://docs.joeywallet.xyz/",
    )

    assert result == root
    page = root / "overview" / "getting-started.md"
    assert page.is_file()
    assert "Content of" in page.read_text(encoding="utf-8")
    assert "https://example.com/other.md" not in fetched


def test_ensure_web_docs_skips_download_when_present_and_no_update(tmp_path):
    root = tmp_path / "joey-docs"
    root.mkdir()
    (root / "welcome.md").write_text("# Welcome", encoding="utf-8")

    result = ensure_web_docs(
        root,
        llms_txt_url="https://docs.joeywallet.xyz/llms.txt",
        base_url="https://docs.joeywallet.xyz/",
        update=False,
    )
    assert result == root


def test_default_doc_sources_include_wallet_docs():
    by_name = {source.name: source for source in DEFAULT_DOC_SOURCES}
    assert by_name["xaman-docs"].repo_url.endswith("Developer-Help-Center.git")
    assert by_name["xaman-docs"].url_base == "https://docs.xaman.dev/"
    assert by_name["joey-docs"].llms_txt_url == "https://docs.joeywallet.xyz/llms.txt"
    assert by_name["joey-docs"].url_base == "https://docs.joeywallet.xyz/"


def test_github_blob_url_base_keeps_full_path_and_suffix():
    from xrpl_rag.parser import derive_source_url

    url = derive_source_url(
        "XLS-0020-nfts/README.md",
        "https://github.com/XRPLF/XRPL-Standards/blob/master/",
    )
    assert url == (
        "https://github.com/XRPLF/XRPL-Standards/blob/master/XLS-0020-nfts/README.md"
    )
    docs_url = derive_source_url(
        "docs/build-clio.md", "https://github.com/XRPLF/clio/blob/develop/"
    )
    assert docs_url == "https://github.com/XRPLF/clio/blob/develop/docs/build-clio.md"


def test_dot_directories_are_skipped(tmp_path):
    from xrpl_rag.docs_source import iter_document_files

    keep = tmp_path / "XLS-0020-nfts" / "README.md"
    skip = tmp_path / ".github" / "copilot-instructions.md"
    skip2 = tmp_path / ".claude" / "skills" / "thing" / "SKILL.md"
    for f in (keep, skip, skip2):
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("# Doc", encoding="utf-8")

    assert list(iter_document_files(tmp_path, {".md"})) == [keep]


def test_ensure_web_docs_skips_pages_that_fail_to_fetch(monkeypatch, tmp_path):
    import urllib.error

    def fake_fetch(url):
        if url.endswith("llms.txt"):
            return LLMS_TXT
        if "getting-started" in url:
            raise urllib.error.HTTPError(url, 404, "Not Found", None, None)
        return "# Page"

    monkeypatch.setattr("xrpl_rag.docs_source._fetch_text", fake_fetch)

    root = tmp_path / "joey-docs"
    ensure_web_docs(
        root,
        llms_txt_url="https://docs.joeywallet.xyz/llms.txt",
        base_url="https://docs.joeywallet.xyz/",
    )
    assert (root / "welcome-to-joey-wallet.md").is_file()
    assert not (root / "overview" / "getting-started.md").exists()
