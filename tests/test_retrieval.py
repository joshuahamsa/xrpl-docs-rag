from xrpl_rag.retrieval import results_from_chroma_query


def test_results_from_chroma_query_maps_documents_metadata_and_distances():
    query = {
        "documents": [["Ticket text", "Payment text"]],
        "metadatas": [
            [
                {
                    "title": "Tickets",
                    "heading_path": "Tickets",
                    "url": "https://xrpl.org/docs/tutorials/tickets",
                    "source_path": "docs/tutorials/tickets.md",
                },
                {
                    "title": "Payment",
                    "heading_path": "Payment",
                    "url": "https://xrpl.org/docs/references/protocol/transactions/payment",
                    "source_path": "docs/references/protocol/transactions/payment.md",
                },
            ]
        ],
        "distances": [[0.2, 0.7]],
    }

    results = results_from_chroma_query(query)

    assert [result.title for result in results] == ["Tickets", "Payment"]
    assert [result.text for result in results] == ["Ticket text", "Payment text"]
    assert results[0].score == 0.8333333333333334
    assert results[1].score == 0.5882352941176471


def test_results_from_chroma_query_handles_empty_response():
    assert results_from_chroma_query({"documents": [], "metadatas": []}) == []
