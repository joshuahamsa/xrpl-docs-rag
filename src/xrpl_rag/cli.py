from __future__ import annotations

from pathlib import Path

import typer

from xrpl_rag.chunker import chunk_page
from xrpl_rag.code_map.pipeline import map_codebase
from xrpl_rag.config import RagConfig
from xrpl_rag.docs_source import (
    DEFAULT_DOC_SOURCES,
    DocsSource,
    ensure_docs_repo,
    ensure_web_docs,
    iter_document_files,
)
from xrpl_rag.formatting import format_context, format_search_results
from xrpl_rag.parser import parse_document_file
from xrpl_rag.retrieval import retrieve
from xrpl_rag.store import VectorStore


app = typer.Typer(help="Local RAG pipeline for XRPL docs and client libraries.")


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
        chunks, file_count, source_count = _ingest_chunks(config, update, docs_path)

        if not chunks:
            raise RuntimeError("No indexable XRPL docs chunks were produced.")

        # Stale deletion is only safe when every default source was scanned;
        # legacy --docs-path mode sees a single source and would wipe the rest.
        added, removed, unchanged = VectorStore(config).sync_chunks(
            chunks, delete_stale=docs_path is None
        )
    except Exception as exc:
        typer.secho(f"ingest failed: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc

    typer.echo(
        f"Indexed {len(chunks)} chunks from {file_count} files across "
        f"{source_count} sources."
    )
    typer.echo(
        f"Embedded {added} new chunks; {unchanged} unchanged, {removed} removed."
    )
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


def _ingest_chunks(
    config: RagConfig, update: bool, docs_path: Path | None
):
    chunks = []
    file_count = 0
    sources = _sources_for_ingest(config, docs_path)

    for source in sources:
        if source.llms_txt_url:
            repo_root = ensure_web_docs(
                source.path,
                llms_txt_url=source.llms_txt_url,
                base_url=source.url_base,
                update=update,
            )
        else:
            repo_root = ensure_docs_repo(
                source.path, update=update, repo_url=source.repo_url
            )
        files = list(
            iter_document_files(
                repo_root,
                source.file_suffixes,
                include_parts=source.include_parts,
            )
        )
        if not files:
            raise RuntimeError(f"No supported docs files found under {repo_root}")

        file_count += len(files)
        for file_path in files:
            try:
                page = parse_document_file(
                    file_path,
                    repo_root,
                    url_base=source.url_base,
                    source_url_base=source.source_url_base,
                    source_name=source.name,
                    prefix_source_path=source.prefix_source_path,
                )
                chunks.extend(chunk_page(page))
            except UnicodeDecodeError:
                continue

    # Identical repeated sections within a page hash to the same chunk_id;
    # Chroma rejects duplicate IDs in one upsert, so keep the first occurrence.
    unique_chunks = list({chunk.chunk_id: chunk for chunk in chunks}.values())
    return unique_chunks, file_count, len(sources)


def _sources_for_ingest(
    config: RagConfig, docs_path: Path | None
) -> tuple[DocsSource, ...]:
    if docs_path is not None:
        return (
            DocsSource(
                name="xrpl-docs",
                repo_url=DEFAULT_DOC_SOURCES[0].repo_url,
                path=config.docs_path,
                url_base=DEFAULT_DOC_SOURCES[0].url_base,
                file_suffixes=DEFAULT_DOC_SOURCES[0].file_suffixes,
                include_parts=DEFAULT_DOC_SOURCES[0].include_parts,
            ),
        )

    sources: list[DocsSource] = []
    for source in DEFAULT_DOC_SOURCES:
        path = (
            config.docs_path
            if source.name == "xrpl-docs"
            else _resolve_path(source.path)
        )
        sources.append(
            DocsSource(
                name=source.name,
                repo_url=source.repo_url,
                path=path,
                url_base=source.url_base,
                prefix_source_path=source.prefix_source_path,
                file_suffixes=source.file_suffixes,
                include_parts=source.include_parts,
                source_url_base=source.source_url_base,
                llms_txt_url=source.llms_txt_url,
            )
        )
    return tuple(sources)


def _resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else Path.cwd() / path


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
