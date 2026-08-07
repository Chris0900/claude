#!/usr/bin/env python3
import argparse
import hashlib
import importlib.metadata
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple

from cache_store import (
    CACHE_SCHEMA_VERSION,
    atomic_write_json,
    atomic_write_text,
    invocation_report,
    load_cache,
    store_cache,
)
from pdf_pipeline import process_document

DEFAULT_MAX_MB = 200.0
PDF_HEADER_SCAN_BYTES = 1024
STRICT_REVIEW_EXIT = 3


class InputError(Exception):
    pass


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Convert a PDF to page-anchored Markdown and emit a machine-readable "
            "quality report. Processing is local; this command does not run OCR."
        )
    )
    parser.add_argument("source", type=Path, help="PDF file to convert")
    parser.add_argument("--output", type=Path, help="Markdown output path")
    parser.add_argument("--report", type=Path, help="JSON quality-report path")
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path.home() / ".cache" / "fast-pdf-to-markdown",
        help="Content-addressed cache directory",
    )
    parser.add_argument(
        "--force", action="store_true", help="Bypass a valid cache entry"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return exit 3 when OCR or visual review is required",
    )
    parser.add_argument(
        "--max-mb",
        type=float,
        default=DEFAULT_MAX_MB,
        help="Reject inputs larger than this many MiB",
    )
    return parser.parse_args(argv)


def resolve_paths(args: argparse.Namespace) -> Tuple[Path, Path, Path, Path]:
    source = args.source.expanduser().resolve()
    output = (args.output or source.with_suffix(".md")).expanduser().resolve()
    report = (args.report or output.with_suffix(".report.json")).expanduser().resolve()
    cache_dir = args.cache_dir.expanduser().resolve()
    if output == source or report == source:
        raise InputError("output and report paths must not overwrite the source PDF")
    if output == report:
        raise InputError("output and report paths must be different")
    return source, output, report, cache_dir


def validate_source(source: Path, max_mb: float) -> int:
    if max_mb <= 0:
        raise InputError("--max-mb must be greater than zero")
    if not source.exists():
        raise InputError("input file does not exist: {}".format(source))
    if not source.is_file():
        raise InputError("input path is not a file: {}".format(source))
    size = source.stat().st_size
    if size > int(max_mb * 1024 * 1024):
        raise InputError(
            "input PDF exceeds --max-mb ({:.2f} MiB > {:.2f} MiB)".format(
                size / 1024 / 1024, max_mb
            )
        )
    with source.open("rb") as handle:
        header = handle.read(PDF_HEADER_SCAN_BYTES)
    if b"%PDF-" not in header:
        raise InputError("input is not a PDF (missing %PDF- header): {}".format(source))
    return size


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parser_version() -> str:
    try:
        return importlib.metadata.version("pdf-inspector")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def cache_key(source_sha256: str, version: str) -> str:
    material = "{}:{}:{}".format(CACHE_SCHEMA_VERSION, version, source_sha256)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def emit_summary(payload: Dict[str, Any]) -> None:
    summary = {
        "status": payload["quality"]["status"],
        "cache_hit": payload["cache"]["hit"],
        "page_count": payload["document"]["page_count"],
        "output": payload["output"]["markdown_path"],
        "report": payload["output"]["report_path"],
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


def run(args: argparse.Namespace) -> int:
    source, output, report, cache_dir = resolve_paths(args)
    size = validate_source(source, args.max_mb)
    source_sha256 = sha256_file(source)
    version = parser_version()
    key = cache_key(source_sha256, version)
    entry = cache_dir / key

    cached = None
    if not args.force and not args.strict:
        cached = load_cache(entry, source_sha256, version)
    if cached is None:
        markdown, base_report = process_document(
            source, size, source_sha256, version
        )
        store_cache(entry, markdown, base_report)
        cache_hit = False
    else:
        markdown, base_report = cached
        cache_hit = True

    payload = invocation_report(
        base_report, source, output, report, key=key, hit=cache_hit
    )
    atomic_write_text(output, markdown)
    atomic_write_json(report, payload)
    emit_summary(payload)
    if args.strict and payload["quality"]["status"] != "clean":
        return STRICT_REVIEW_EXIT
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    try:
        return run(parse_args(argv))
    except InputError as error:
        print("error: {}".format(error), file=sys.stderr)
        return 2
    except Exception as error:
        print("error: PDF conversion failed: {}".format(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
