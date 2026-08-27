from xrpl_rag.chunker import chunk_page
from xrpl_rag.parser import ParsedPage


def test_chunk_page_includes_title_heading_and_stable_ids():
    page = ParsedPage(
        source_path="docs/concepts/accounts/index.md",
        title="Accounts",
        url="https://xrpl.org/docs/concepts/accounts",
        text="# Accounts\n\nIntro text.\n\n## Creating Accounts\n\nFund an address.",
        headings=["Accounts", "Creating Accounts"],
    )

    first = chunk_page(page, max_words=20, overlap_words=3)
    second = chunk_page(page, max_words=20, overlap_words=3)

    assert len(first) == 2
    assert first[0].title == "Accounts"
    assert first[1].heading_path == "Accounts > Creating Accounts"
    assert "Title: Accounts" in first[1].embedding_text
    assert "Heading: Accounts > Creating Accounts" in first[1].embedding_text
    assert [chunk.chunk_id for chunk in first] == [chunk.chunk_id for chunk in second]


def test_chunk_page_splits_long_sections_with_overlap():
    words = [f"word{i}" for i in range(18)]
    page = ParsedPage(
        source_path="docs/tutorials/tickets.md",
        title="Tickets",
        url="https://xrpl.org/docs/tutorials/tickets",
        text="# Tickets\n\n" + " ".join(words),
        headings=["Tickets"],
    )

    chunks = chunk_page(page, max_words=10, overlap_words=2)

    assert len(chunks) == 2
    assert chunks[0].text.split()[-2:] == chunks[1].text.split()[:2]
    assert chunks[0].chunk_id != chunks[1].chunk_id

