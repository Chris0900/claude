import contextlib
import hashlib
import importlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, Optional
from unittest import mock

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "convert_pdf.py"


def write_minimal_pdf(path: Path, text: Optional[str] = "Hello PDF") -> None:
    content = b"" if text is None else (
        f"BT /F1 18 Tf 72 720 Td ({text}) Tj ET\n".encode("ascii")
    )
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n"
        + content
        + b"endstream",
    ]
    payload = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(payload))
        payload.extend(f"{index} 0 obj\n".encode("ascii"))
        payload.extend(obj)
        payload.extend(b"\nendobj\n")
    xref_offset = len(payload)
    payload.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    payload.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        payload.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    payload.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    path.write_bytes(payload)


class FastPdfToMarkdownTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_converts_text_pdf_with_page_anchors(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.pdf"
            output = root / "source.md"
            report = root / "source.json"
            cache = root / "cache"
            write_minimal_pdf(source)

            result = self.run_cli(
                str(source),
                "--output",
                str(output),
                "--report",
                str(report),
                "--cache-dir",
                str(cache),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.read_text(encoding="utf-8").count("<!-- Page 1 -->"), 1)
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(payload["document"]["page_count"], 1)
            self.assertEqual(payload["output"]["page_markers"], 1)
            self.assertEqual(payload["quality"]["status"], "clean")

    def test_rejects_non_pdf_without_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "invalid.bin"
            output = root / "invalid.md"
            report = root / "invalid.json"
            source.write_bytes(b"not a pdf")

            result = self.run_cli(
                str(source), "--output", str(output), "--report", str(report)
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("not a PDF", result.stderr)
            self.assertFalse(output.exists())
            self.assertFalse(report.exists())

    def test_reuses_hash_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.pdf"
            output = root / "source.md"
            report = root / "source.json"
            cache = root / "cache"
            write_minimal_pdf(source)
            args = (
                str(source),
                "--output",
                str(output),
                "--report",
                str(report),
                "--cache-dir",
                str(cache),
            )

            first = self.run_cli(*args)
            self.assertEqual(first.returncode, 0, first.stderr)
            first_hash = hashlib.sha256(output.read_bytes()).hexdigest()
            second = self.run_cli(*args)

            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertTrue(json.loads(second.stdout)["cache_hit"])
            self.assertTrue(json.loads(report.read_text(encoding="utf-8"))["cache"]["hit"])
            self.assertEqual(hashlib.sha256(output.read_bytes()).hexdigest(), first_hash)

    def test_rebuilds_tampered_cache_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.pdf"
            output = root / "source.md"
            report = root / "source.json"
            cache = root / "cache"
            write_minimal_pdf(source)
            args = (
                str(source),
                "--output",
                str(output),
                "--report",
                str(report),
                "--cache-dir",
                str(cache),
            )

            first = self.run_cli(*args)
            self.assertEqual(first.returncode, 0, first.stderr)
            original_hash = hashlib.sha256(output.read_bytes()).hexdigest()
            key = json.loads(report.read_text(encoding="utf-8"))["cache"]["key"]
            (cache / key / "document.md").write_text(
                "<!-- Page 1 -->\n\nTAMPERED\n", encoding="utf-8"
            )

            second = self.run_cli(*args)

            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertFalse(json.loads(second.stdout)["cache_hit"])
            self.assertFalse(
                json.loads(report.read_text(encoding="utf-8"))["cache"]["hit"]
            )
            self.assertEqual(hashlib.sha256(output.read_bytes()).hexdigest(), original_hash)

            metadata_path = cache / key / "metadata.json"
            manifest_path = cache / key / "manifest.json"
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata["quality"]["status"] = "trusted"
            metadata_path.write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["metadata_sha256"] = hashlib.sha256(
                metadata_path.read_bytes()
            ).hexdigest()
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            third = self.run_cli(*args)

            self.assertEqual(third.returncode, 0, third.stderr)
            self.assertFalse(json.loads(third.stdout)["cache_hit"])
            self.assertEqual(hashlib.sha256(output.read_bytes()).hexdigest(), original_hash)

    def test_strict_force_returns_exact_review_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.pdf"
            output = root / "source.md"
            report = root / "source.json"
            cache = root / "cache"
            write_minimal_pdf(source)
            scripts_dir = str(SCRIPT.parent)
            if scripts_dir not in sys.path:
                sys.path.insert(0, scripts_dir)
            convert_pdf = importlib.import_module("convert_pdf")

            source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
            base_report: Dict[str, Any] = {
                "schema_version": convert_pdf.CACHE_SCHEMA_VERSION,
                "document": {
                    "sha256": source_hash,
                    "bytes": source.stat().st_size,
                    "page_count": 1,
                    "pdf_type": "text_based",
                    "confidence": 1.0,
                },
                "parser": {
                    "name": "pdf-inspector",
                    "version": convert_pdf.parser_version(),
                    "processing_time_ms": 1,
                    "local_only": True,
                    "ocr_performed": False,
                },
                "quality": {
                    "status": "review_required",
                    "warnings": [{"code": "tables_detected", "pages": [1]}],
                },
                "output": {
                    "markdown_bytes": 32,
                    "markdown_characters": 32,
                    "page_markers": 1,
                },
            }
            markdown = "<!-- Page 1 -->\n\n| A | B |\n"
            base_report["output"]["markdown_bytes"] = len(markdown.encode("utf-8"))
            base_report["output"]["markdown_characters"] = len(markdown)
            args = convert_pdf.parse_args(
                [
                    str(source),
                    "--output",
                    str(output),
                    "--report",
                    str(report),
                    "--cache-dir",
                    str(cache),
                    "--strict",
                    "--force",
                ]
            )

            with mock.patch.object(
                convert_pdf,
                "process_document",
                return_value=(markdown, base_report),
            ) as process:
                with contextlib.redirect_stdout(io.StringIO()):
                    result = convert_pdf.run(args)

            self.assertEqual(result, 3)
            process.assert_called_once()
            self.assertTrue(output.exists())
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(payload["quality"]["status"], "review_required")
            self.assertFalse(payload["cache"]["hit"])


if __name__ == "__main__":
    unittest.main()
