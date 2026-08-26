from pathlib import Path

from xrpl_rag.chunker import chunk_page
from xrpl_rag.parser import derive_docs_url, parse_document_file, parse_markdown_file


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


def test_parse_document_file_extracts_rst_headings_and_directives(tmp_path):
    repo_root = tmp_path / "xrpl-py"
    page_path = repo_root / "docs" / "source" / "xrpl.transaction.rst"
    page_path.parent.mkdir(parents=True)
    page_path.write_text(
        """Transaction Methods
===================

Methods for working with transactions on the XRP Ledger.

.. automodule:: xrpl.transaction
   :members:
   :undoc-members:

Autofill
--------

Use ``autofill`` before signing.
""",
        encoding="utf-8",
    )

    page = parse_document_file(
        page_path,
        repo_root,
        url_base="https://xrpl-py.readthedocs.io/en/stable/",
        source_name="xrpl-py",
    )

    assert page.source_name == "xrpl-py"
    assert page.source_path == "xrpl-py:docs/source/xrpl.transaction.rst"
    assert page.title == "Transaction Methods"
    assert page.url == (
        "https://xrpl-py.readthedocs.io/en/stable/source/xrpl.transaction.html"
    )
    assert page.headings == ["Transaction Methods", "Autofill"]
    assert "Methods for working with transactions" in page.text
    assert "Use `autofill` before signing." in page.text
    assert "automodule" not in page.text


def test_parse_document_file_extracts_typedoc_html_text_and_code(tmp_path):
    repo_root = tmp_path / "xrpl.js"
    page_path = repo_root / "docs" / "classes" / "Client.html"
    page_path.parent.mkdir(parents=True)
    page_path.write_text(
        """<!doctype html>
<html>
  <head><title>Client | xrpl</title><script>ignore()</script></head>
  <body>
    <nav>Navigation</nav>
    <h1>Class Client</h1>
    <section>
      <p>Client for interacting with rippled servers.</p>
      <h3><span>submit<wbr/>And<wbr/>Wait</span></h3>
      <p>Submits a transaction and waits for validation.</p>
      <pre><code>const client = new Client(url)</code><button>Copy</button></pre>
    </section>
  </body>
</html>
""",
        encoding="utf-8",
    )

    page = parse_document_file(
        page_path,
        repo_root,
        url_base="https://js.xrpl.org/",
        source_name="xrpl-js",
    )

    assert page.source_name == "xrpl-js"
    assert page.source_path == "xrpl-js:docs/classes/Client.html"
    assert page.title == "Class Client"
    assert page.url == "https://js.xrpl.org/classes/Client.html"
    assert page.headings == ["Class Client", "submitAndWait"]
    assert "Client for interacting with rippled servers." in page.text
    assert "const client = new Client(url)" in page.text
    assert "ignore()" not in page.text


def test_parse_document_file_extracts_python_docstrings(tmp_path):
    repo_root = tmp_path / "xrpl-py"
    page_path = repo_root / "xrpl" / "transaction" / "main.py"
    page_path.parent.mkdir(parents=True)
    page_path.write_text(
        '"""High-level transaction methods with XRPL transactions."""\n\n'
        "def autofill(transaction, client):\n"
        '    """Autofills fields in a transaction.\n\n'
        "    Args:\n"
        "        transaction: the transaction to be signed.\n"
        "        client: a network client.\n"
        '    """\n'
        "    return transaction\n",
        encoding="utf-8",
    )

    page = parse_document_file(
        page_path,
        repo_root,
        url_base="https://xrpl-py.readthedocs.io/en/stable/",
        source_url_base="https://github.com/XRPLF/xrpl-py/blob/main/",
        source_name="xrpl-py",
    )

    assert page.source_name == "xrpl-py"
    assert page.source_path == "xrpl-py:xrpl/transaction/main.py"
    assert page.title == "xrpl.transaction.main"
    assert page.url == "https://github.com/XRPLF/xrpl-py/blob/main/xrpl/transaction/main.py"
    assert page.headings == ["xrpl.transaction.main", "autofill"]
    assert "High-level transaction methods" in page.text
    assert "def autofill(transaction, client)" in page.text
    assert "Autofills fields in a transaction." in page.text


def test_non_markdown_headings_create_chunk_heading_paths(tmp_path):
    repo_root = tmp_path / "xrpl.js"
    page_path = repo_root / "docs" / "classes" / "Client.html"
    page_path.parent.mkdir(parents=True)
    page_path.write_text(
        "<html><body><h1>Class Client</h1><p>Overview.</p>"
        "<h3><span>submit<wbr/>And<wbr/>Wait</span></h3>"
        "<p>Waits for validation.</p></body></html>",
        encoding="utf-8",
    )

    page = parse_document_file(
        page_path,
        repo_root,
        url_base="https://js.xrpl.org/",
        source_name="xrpl-js",
    )
    chunks = chunk_page(page)

    assert [chunk.heading_path for chunk in chunks] == [
        "Class Client",
        "Class Client > submitAndWait",
    ]
