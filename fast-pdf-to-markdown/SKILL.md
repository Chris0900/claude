---
name: fast-pdf-to-markdown
description: Convert authorized local PDF files into fast, searchable, page-anchored Markdown with a JSON quality report and content-addressed cache. Use for reading, indexing, searching, chunking, comparing, or preparing RAG/quiz evidence from PDFs, especially before expensive OCR; route scanned, garbled, table-heavy, or multi-column pages to selective OCR or visual verification instead of trusting native extraction silently.
---

# Fast PDF to Markdown

Use `pdf-inspector` as a local fast path. Treat the Markdown as a searchable index and keep the original PDF as the source of truth for layout, figures, tables, and exact page evidence.

## Convert

Run the deterministic converter by its installed path with a pinned package version:

```bash
uv run --with pdf-inspector==0.2.6 python ~/.claude/skills/fast-pdf-to-markdown/scripts/convert_pdf.py input.pdf \
  --output output.md \
  --report output.report.json
```

The converter processes files locally and does not perform OCR or upload content. It writes `<!-- Page N -->` anchors before every extracted page and prints a compact JSON summary to stdout.

Use `--force` to bypass the content-addressed cache. Cache hits require matching content digests and report semantics; corrupt entries are rebuilt. `--strict` always reprocesses the PDF instead of trusting cached quality metadata. Use `--cache-dir PATH` when evidence must remain inside a project-specific directory. The default cache is `~/.cache/fast-pdf-to-markdown`.

## Interpret the report

Read `quality.status` before using the Markdown:

- `clean`: Use for search, summarization, and chunking. Recheck the original page for exact quotations or layout-sensitive claims.
- `review_required`: Inspect pages listed under `pages_with_tables`, `pages_with_columns`, or warnings such as `low_text_coverage`. Native text may be present but reading order or Markdown structure can be wrong.
- `ocr_required`: Render and OCR only `pages_needing_ocr`; do not rerun OCR over clean text pages.

Use `--strict` for evidence-sensitive work. Exit `3` means the Markdown and report were written, but review or OCR remains required. Exit `2` means the input or arguments are invalid. Exit `1` means conversion failed.

## Verify risky pages

Render the page numbers named by the report and compare them with the corresponding Markdown blocks:

```bash
pdftoppm -f 7 -l 7 -png -r 150 input.pdf page-7
```

Check column order, table cells, headings, footnotes, diagrams, and Korean character integrity. Use the existing `pdf` skill for layout-focused visual review. Never infer text contained only in images from native extraction.

## Preserve evidence boundaries

- Process only files the user is authorized to access; never bypass DRM or access controls.
- Preserve page anchors when chunking or generating citations.
- Keep the original PDF beside derived Markdown for disputes and final verification.
- State explicitly when OCR or visual review was not completed.
- Do not describe `review_required` or `ocr_required` output as a verified complete reading.
