import importlib
import re
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from cache_store import CACHE_SCHEMA_VERSION

MIN_COVERAGE_RATIO = 0.85


def unique_sorted(values: Iterable[int]) -> List[int]:
    return sorted(set(int(value) for value in values))


def build_markdown(pages: Iterable[Any]) -> Tuple[str, int]:
    blocks: List[str] = []
    for page in sorted(pages, key=lambda item: int(item.page)):
        page_number = int(page.page) + 1
        body = (page.markdown or "").strip()
        block = "<!-- Page {} -->".format(page_number)
        if body:
            block += "\n\n" + body
        blocks.append(block)
    markdown = "\n\n".join(blocks)
    if markdown:
        markdown += "\n"
    return markdown, len(blocks)


def visible_character_count(text: str, markdown: bool = False) -> int:
    if markdown:
        text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
        text = re.sub(r"[`*_#>|]", "", text)
        text = re.sub(r"(?m)^\s*(?:[-+] |\d+[.)] )", "", text)
    return len(re.sub(r"\s+", "", text))


def has_encoding_issue(markdown: str, reasons: Iterable[str]) -> bool:
    if "\ufffd" in markdown:
        return True
    suspicious = ("encoding", "garbled", "gid", "tounicode", "unicode")
    return any(
        any(token in str(reason).lower() for token in suspicious) for reason in reasons
    )


def quality_report(
    markdown: str,
    raw_text: str,
    page_count: int,
    extracted_page_count: int,
    pages_needing_ocr: List[int],
    pages_with_tables: List[int],
    pages_with_columns: List[int],
    ocr_reasons_by_page: List[Dict[str, Any]],
) -> Dict[str, Any]:
    raw_chars = visible_character_count(raw_text)
    markdown_chars = visible_character_count(markdown, markdown=True)
    coverage_ratio: Optional[float]
    if raw_chars:
        coverage_ratio = round(min(markdown_chars / raw_chars, 1.0), 4)
    elif markdown_chars:
        coverage_ratio = 1.0
    else:
        coverage_ratio = None

    reasons = [
        reason
        for entry in ocr_reasons_by_page
        for reason in entry.get("reasons", [])
    ]
    encoding_issue = has_encoding_issue(markdown, reasons)
    warnings: List[Dict[str, Any]] = []
    if pages_needing_ocr:
        warnings.append({"code": "ocr_required", "pages": pages_needing_ocr})
    if encoding_issue:
        warnings.append({"code": "encoding_issue"})
    if coverage_ratio is not None and coverage_ratio < MIN_COVERAGE_RATIO:
        warnings.append(
            {
                "code": "low_text_coverage",
                "ratio": coverage_ratio,
                "minimum": MIN_COVERAGE_RATIO,
            }
        )
    if pages_with_tables:
        warnings.append({"code": "tables_detected", "pages": pages_with_tables})
    if pages_with_columns:
        warnings.append({"code": "columns_detected", "pages": pages_with_columns})
    if page_count != extracted_page_count:
        warnings.append(
            {
                "code": "page_count_mismatch",
                "classified": page_count,
                "extracted": extracted_page_count,
            }
        )

    if pages_needing_ocr or encoding_issue:
        status = "ocr_required"
    elif warnings:
        status = "review_required"
    else:
        status = "clean"
    return {
        "status": status,
        "has_encoding_issues": encoding_issue,
        "coverage_ratio": coverage_ratio,
        "raw_text_characters": raw_chars,
        "markdown_text_characters": markdown_chars,
        "pages_needing_ocr": pages_needing_ocr,
        "pages_with_tables": pages_with_tables,
        "pages_with_columns": pages_with_columns,
        "ocr_reasons_by_page": ocr_reasons_by_page,
        "warnings": warnings,
    }


def normalise_ocr_reasons(entries: Iterable[Any]) -> List[Dict[str, Any]]:
    normalised: List[Dict[str, Any]] = []
    for entry in entries:
        if isinstance(entry, dict):
            page = int(entry.get("page", 0))
            reasons = [str(value) for value in entry.get("reasons", [])]
        else:
            page = int(getattr(entry, "page", 0))
            reasons = [str(value) for value in getattr(entry, "reasons", [])]
        normalised.append({"page": page, "reasons": reasons})
    return normalised


def process_document(
    source: Path,
    size: int,
    source_sha256: str,
    parser_version: str,
) -> Tuple[str, Dict[str, Any]]:
    started = time.perf_counter()
    pdf_inspector = importlib.import_module("pdf_inspector")
    classification = pdf_inspector.classify_pdf(str(source))
    extraction = pdf_inspector.extract_pages_markdown(str(source))
    raw_text = pdf_inspector.extract_text(str(source))
    elapsed_ms = round((time.perf_counter() - started) * 1000)

    classified_ocr = [int(page) + 1 for page in classification.pages_needing_ocr]
    pages_needing_ocr = unique_sorted(
        list(extraction.pages_needing_ocr) + classified_ocr
    )
    pages_with_tables = unique_sorted(extraction.pages_with_tables)
    pages_with_columns = unique_sorted(extraction.pages_with_columns)
    reasons = normalise_ocr_reasons(extraction.ocr_reasons_by_page)
    markdown, page_markers = build_markdown(extraction.pages)
    quality = quality_report(
        markdown,
        raw_text,
        int(classification.page_count),
        len(extraction.pages),
        pages_needing_ocr,
        pages_with_tables,
        pages_with_columns,
        reasons,
    )
    base_report: Dict[str, Any] = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "document": {
            "sha256": source_sha256,
            "bytes": size,
            "page_count": int(classification.page_count),
            "pdf_type": str(classification.pdf_type),
            "confidence": float(classification.confidence),
        },
        "parser": {
            "name": "pdf-inspector",
            "version": parser_version,
            "processing_time_ms": elapsed_ms,
            "local_only": True,
            "ocr_performed": False,
        },
        "quality": quality,
        "output": {
            "markdown_bytes": len(markdown.encode("utf-8")),
            "markdown_characters": len(markdown),
            "page_markers": page_markers,
        },
    }
    return markdown, base_report
