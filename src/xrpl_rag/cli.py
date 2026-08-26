from __future__ import annotations

from pathlib import Path

import typer

from xrpl_rag.chunker import chunk_page
from xrpl_rag.code_map.pipeline import map_codebase
from xrpl_rag.config import RagConfig
from xrpl_rag.docs_source import ensure_docs_repo, iter_markdown_files
from xrpl_rag.formatting import format_context, format_search_results
from xrpl_rag.parser import parse_markdown_file
from xrpl_rag.retrieval import retrieve
from xrpl_rag.store import VectorStore


app = typer.Typer(help="Local RAG pipeline for the official XRPL docs.")


@app.command()
def ingest(
    docs_path: Path | None = typer.Option(
        None, "--docs-path", help="Use an existing xrpl-dev-portal checkout."
    ),
    update: bool = typer.Option(
        True, "--update/--no-update", help="Clone or update the docs repository."
    ),
):
    config = _config(docs_path)
    try:
        repo_root = ensure_docs_repo(config.docs_path, update=update)
        files = list(iter_markdown_files(repo_root))
        if not files:
            raise RuntimeError(f"No Markdown or MDX files found under {repo_root}")

        chunks = []
        for file_path in files:
            try:
                chunks.extend(chunk_page(parse_markdown_file(file_path, repo_root)))
            except UnicodeDecodeError:
                continue

        if not chunks:
            raise RuntimeError("No indexable XRPL docs chunks were produced.")

        VectorStore(config).upsert_chunks(chunks)
    except Exception as exc:
        typer.secho(f"ingest failed: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc

    typer.echo(f"Indexed {len(chunks)} chunks from {len(files)} files.")
    typer.echo(f"Vector DB: {config.db_path}")


@app.command()
def search(
    question: str = typer.Argument(..., help="Question or keywords to search for."),
    top_k: int = typer.Option(5, "--top-k", min=1, help="Number of chunks to return."),
    docs_path: Path | None = typer.Option(None, "--docs-path", help="Override docs path."),
):
    config = _config(docs_path)
    try:
        typer.echo(format_search_results(retrieve(question, config, top_k=top_k)))
    except Exception as exc:
        typer.secho(
            f"search failed: {exc}\nRun `xrpl-rag ingest` first if the vector store is empty.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(1) from exc


@app.command()
def context(
    question: str = typer.Argument(..., help="Question to prepare context for."),
    top_k: int = typer.Option(5, "--top-k", min=1, help="Number of chunks to include."),
    docs_path: Path | None = typer.Option(None, "--docs-path", help="Override docs path."),
):
    config = _config(docs_path)
    try:
        typer.echo(format_context(question, retrieve(question, config, top_k=top_k)))
    except Exception as exc:
        typer.secho(
            f"context failed: {exc}\nRun `xrpl-rag ingest` first if the vector store is empty.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(1) from exc


@app.command("map-code")
def map_code(
    codebase_path: Path = typer.Argument(..., help="Repository or source tree to map."),
    out_dir: Path = typer.Option(Path(".rag/code-map"), "--out", help="Output directory."),
    output_format: str = typer.Option(
        "both", "--format", help="Output format: jsonl, markdown, or both."
    ),
    include: list[str] | None = typer.Option(
        None, "--include", help="Glob pattern to include. Repeat for multiple patterns."
    ),
    exclude: list[str] | None = typer.Option(
        None, "--exclude", help="Glob pattern to exclude. Repeat for multiple patterns."
    ),
    max_code_chars: int = typer.Option(
        12_000, "--max-code-chars", min=200, help="Maximum code characters per record."
    ),
    progress: bool = typer.Option(
        True, "--progress/--no-progress", help="Print progress updates to stderr."
    ),
    progress_every: int = typer.Option(
        100, "--progress-every", min=1, help="Files between progress updates."
    ),
    throttle_ms: int = typer.Option(
        0, "--throttle-ms", min=0, help="Sleep this many milliseconds after each file."
    ),
):
    try:
        result = map_codebase(
            codebase_path,
            out_dir,
            output_format=output_format,
            include=include,
            exclude=exclude,
            max_code_chars=max_code_chars,
            progress_callback=_progress_reporter if progress else None,
            progress_every=progress_every,
            throttle_ms=throttle_ms,
        )
    except Exception as exc:
        typer.secho(f"map-code failed: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc

    typer.echo(
        f"Mapped {len(result.records)} records from {len(result.source_files)} files."
    )
    for name, path in result.outputs.items():
        typer.echo(f"{name}: {path}")
    for warning in result.warnings:
        typer.secho(f"warning: {warning}", fg=typer.colors.YELLOW, err=True)


def _progress_reporter(message: str) -> None:
    typer.secho(message, fg=typer.colors.BLUE, err=True)


def _config(docs_path: Path | None = None) -> RagConfig:
    config = RagConfig.from_env().resolve(Path.cwd())
    if docs_path is None:
        return config
    return RagConfig(
        docs_path=docs_path,
        db_path=config.db_path,
        collection_name=config.collection_name,
        embedding_model=config.embedding_model,
    ).resolve(Path.cwd())


if __name__ == "__main__":
    app()
