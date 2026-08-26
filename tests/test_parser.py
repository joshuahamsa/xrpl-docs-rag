from pathlib import Path

from xrpl_rag.parser import derive_docs_url, parse_markdown_file


def test_parse_markdown_file_extracts_metadata_and_preserves_code(tmp_path):
    repo_root = tmp_path / "repo"
    page_path = repo_root / "docs" / "concepts" / "accounts" / "index.md"
    page_path.parent.mkdir(parents=True)
    page_path.write_text(
        """---
title: Accounts
description: Account docs.
---

import Example from './Example'

# AccountRoot

XRPL accounts hold XRP.

<Callout>
This line is inside an MDX component.
</Callout>

## Creating Accounts

Use a payment transaction.

```json
{"TransactionType": "Payment"}
```
""",
        encoding="utf-8",
    )

    page = parse_markdown_file(page_path, repo_root)

    assert page.source_path == "docs/concepts/accounts/index.md"
    assert page.title == "Accounts"
    assert page.url == "https://xrpl.org/docs/concepts/accounts"
    assert page.headings == ["AccountRoot", "Creating Accounts"]
    assert "XRPL accounts hold XRP." in page.text
    assert '{"TransactionType": "Payment"}' in page.text
    assert "import Example" not in page.text
    assert "<Callout>" not in page.text


def test_parse_markdown_file_uses_h1_then_file_stem_fallback(tmp_path):
    repo_root = tmp_path / "repo"
    h1_path = repo_root / "docs" / "tutorials" / "tickets.md"
    h1_path.parent.mkdir(parents=True)
    h1_path.write_text("# Tickets\n\nTicket docs.", encoding="utf-8")

    no_h1_path = repo_root / "docs" / "references" / "ledger.md"
    no_h1_path.parent.mkdir(parents=True, exist_ok=True)
    no_h1_path.write_text("Ledger entry docs.", encoding="utf-8")

    assert parse_markdown_file(h1_path, repo_root).title == "Tickets"
    assert parse_markdown_file(no_h1_path, repo_root).title == "ledger"


def test_derive_docs_url_handles_common_xrpl_docs_paths():
    assert (
        derive_docs_url("docs/references/protocol/transactions/payment.md")
        == "https://xrpl.org/docs/references/protocol/transactions/payment"
    )
    assert (
        derive_docs_url("docs/concepts/accounts/index.mdx")
        == "https://xrpl.org/docs/concepts/accounts"
    )
