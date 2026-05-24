"""Local CLI for querying saved references without MCP."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from gtd_assistant.adapters.qwen_embedder import QwenReferenceEmbedder
from gtd_assistant.adapters.sqlite_reference_store import SQLiteReferenceStore
from gtd_assistant.application.search_references import search_references
from gtd_assistant.domain.reference import ReferenceRecord, ReferenceSearchResult
from gtd_assistant.infrastructure.reference_config import load_reference_db_path


def main(argv: Sequence[str] | None = None) -> None:
    """Search the local reference database and print agent-readable Markdown."""
    args = _parse_args(argv)
    query = " ".join(args.query).strip()

    embedder = QwenReferenceEmbedder()
    store = SQLiteReferenceStore(load_reference_db_path(), vector_dimension=embedder.dimension)
    results = search_references(store=store, embedder=embedder, query=query, limit=args.limit)

    print(format_markdown_results(query=query, results=results))


def format_markdown_results(*, query: str, results: list[ReferenceSearchResult]) -> str:
    """Return reference search results in a compact Markdown format for Codex."""
    lines = [
        "# Reference Search Results",
        "",
        f"Query: {query}",
        "",
    ]

    if not results:
        lines.extend(
            [
                "No matching local references were found.",
                "",
                "Answer guidance: say that no strong local references were found.",
            ]
        )
        return "\n".join(lines)

    lines.append(
        "Answer guidance: answer from these local references and cite the relevant URLs or files."
    )
    lines.append("")

    for index, result in enumerate(results, start=1):
        reference = result.reference
        lines.extend(
            [
                f"## {index}. {_clean_text(reference.title) or 'Untitled reference'}",
                f"- id: {reference.id}",
                f"- score: {result.score:.4f}",
            ]
        )
        _append_optional_line(lines, "url", reference.url)
        _append_optional_line(lines, "file", _reference_file_path(reference))
        _append_optional_line(lines, "source", reference.source)
        if reference.tags:
            lines.append(f"- tags: {', '.join(reference.tags)}")
        _append_optional_line(lines, "captured_at", reference.captured_at)
        _append_optional_line(lines, "snippet", result.snippet)
        _append_optional_line(lines, "summary", reference.summary)
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="gtd-references-query",
        description="Search local GTD saved references and print Markdown evidence.",
    )
    parser.add_argument("query", nargs="+", help="Question or search query.")
    parser.add_argument(
        "--limit",
        type=int,
        default=8,
        help="Maximum number of references to return. Defaults to 8.",
    )
    parser.add_argument(
        "--format",
        choices=("markdown",),
        default="markdown",
        help="Output format. Currently only markdown is supported.",
    )
    return parser.parse_args(argv)


def _append_optional_line(lines: list[str], label: str, value: object) -> None:
    text = _clean_text(value)
    if text:
        lines.append(f"- {label}: {text}")


def _reference_file_path(reference: ReferenceRecord) -> str:
    metadata = reference.metadata
    for key in ("file_path", "source_path"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _clean_text(value: object) -> str:
    return " ".join(str(value or "").split())


if __name__ == "__main__":
    main()
