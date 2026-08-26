from xrpl_rag.formatting import (
    SearchResult,
    format_context,
    format_search_results,
)


def test_format_search_results_includes_scores_and_sources():
    results = [
        SearchResult(
            title="Tickets",
            heading_path="Tickets > Creating Tickets",
            url="https://xrpl.org/docs/tutorials/tickets",
            source_path="docs/tutorials/tickets.md",
            text="Tickets reserve transaction sequence numbers.",
            score=0.87,
        )
    ]

    output = format_search_results(results)

    assert "[1] Tickets" in output
    assert "Heading: Tickets > Creating Tickets" in output
    assert "URL: https://xrpl.org/docs/tutorials/tickets" in output
    assert "Source: docs/tutorials/tickets.md" in output
    assert "Score: 0.8700" in output
    assert "Tickets reserve transaction sequence numbers." in output


def test_format_context_omits_scores_and_keeps_question():
    results = [
        SearchResult(
            title="Payment",
            heading_path="Payment transaction",
            url="https://xrpl.org/docs/references/protocol/transactions/payment",
            source_path="docs/references/protocol/transactions/payment.md",
            text="Payment sends XRP or issued currency.",
            score=0.91,
        )
    ]

    output = format_context("How do payments work?", results)

    assert output.startswith("Question: How do payments work?")
    assert "Relevant XRPL docs:" in output
    assert "[1] Payment" in output
    assert "Excerpt: Payment sends XRP or issued currency." in output
    assert "Score:" not in output
