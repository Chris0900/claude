import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

CACHE_SCHEMA_VERSION = 2
VALID_QUALITY_STATUSES = {"clean", "review_required", "ocr_required"}


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def json_bytes(payload: Dict[str, Any]) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def atomic_write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Optional[str] = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=str(path.parent), prefix=".{}-".format(path.name), delete=False
        ) as handle:
            temporary = handle.name
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def atomic_write_text(path: Path, content: str) -> None:
    atomic_write_bytes(path, content.encode("utf-8"))


def atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    atomic_write_bytes(path, json_bytes(payload))


def valid_cached_payload(
    markdown: str,
    metadata: Dict[str, Any],
    expected_source_sha256: str,
    expected_parser_version: str,
) -> bool:
    document = metadata.get("document")
    parser = metadata.get("parser")
    output = metadata.get("output")
    quality = metadata.get("quality")
    if not isinstance(document, dict):
        return False
    if not isinstance(parser, dict):
        return False
    if not isinstance(output, dict):
        return False
    if not isinstance(quality, dict):
        return False
    if metadata.get("schema_version") != CACHE_SCHEMA_VERSION:
        return False
    if document.get("sha256") != expected_source_sha256:
        return False
    if parser.get("version") != expected_parser_version:
        return False
    if parser.get("local_only") is not True or parser.get("ocr_performed") is not False:
        return False
    if quality.get("status") not in VALID_QUALITY_STATUSES:
        return False
    if not isinstance(quality.get("warnings"), list):
        return False

    markdown_bytes = markdown.encode("utf-8")
    if output.get("markdown_bytes") != len(markdown_bytes):
        return False
    if output.get("markdown_characters") != len(markdown):
        return False
    markers = [int(value) for value in re.findall(r"(?m)^<!-- Page ([1-9]\d*) -->$", markdown)]
    if markers != list(range(1, len(markers) + 1)):
        return False
    if output.get("page_markers") != len(markers):
        return False
    return True


def load_cache(
    entry: Path,
    expected_source_sha256: str,
    expected_parser_version: str,
) -> Optional[Tuple[str, Dict[str, Any]]]:
    markdown_path = entry / "document.md"
    metadata_path = entry / "metadata.json"
    manifest_path = entry / "manifest.json"
    if not all(path.is_file() for path in (markdown_path, metadata_path, manifest_path)):
        return None
    try:
        markdown_bytes = markdown_path.read_bytes()
        metadata_bytes = metadata_path.read_bytes()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        metadata = json.loads(metadata_bytes.decode("utf-8"))
        markdown = markdown_bytes.decode("utf-8")
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(manifest, dict) or not isinstance(metadata, dict):
        return None
    if manifest.get("schema_version") != CACHE_SCHEMA_VERSION:
        return None
    if manifest.get("markdown_sha256") != sha256_bytes(markdown_bytes):
        return None
    if manifest.get("metadata_sha256") != sha256_bytes(metadata_bytes):
        return None
    if not valid_cached_payload(
        markdown, metadata, expected_source_sha256, expected_parser_version
    ):
        return None
    return markdown, metadata


def store_cache(entry: Path, markdown: str, metadata: Dict[str, Any]) -> None:
    markdown_bytes = markdown.encode("utf-8")
    metadata_bytes = json_bytes(metadata)
    manifest = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "markdown_sha256": sha256_bytes(markdown_bytes),
        "metadata_sha256": sha256_bytes(metadata_bytes),
    }
    entry.mkdir(parents=True, exist_ok=True)
    atomic_write_bytes(entry / "document.md", markdown_bytes)
    atomic_write_bytes(entry / "metadata.json", metadata_bytes)
    atomic_write_json(entry / "manifest.json", manifest)


def invocation_report(
    base: Dict[str, Any],
    source: Path,
    output: Path,
    report: Path,
    key: str,
    hit: bool,
) -> Dict[str, Any]:
    payload = json.loads(json.dumps(base))
    payload["source"] = {"path": str(source)}
    payload["output"].update(
        {"markdown_path": str(output), "report_path": str(report)}
    )
    payload["cache"] = {"hit": hit, "key": key}
    return payload
