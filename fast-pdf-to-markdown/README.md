[English](README.md) · [한국어](README.ko.md)

# Fast PDF to Markdown

A local Claude Code skill that turns authorized PDFs into searchable, page-anchored Markdown, reports extraction risks, and caches validated results for fast repeat work.

## Quick start

Install the skill in one line:

```bash
git clone https://github.com/NewTurn2017/fast-pdf-to-markdown.git ~/.claude/skills/fast-pdf-to-markdown
```

Convert a PDF with the pinned `pdf-inspector` runtime:

```bash
uv run --with pdf-inspector==0.2.6 python ~/.claude/skills/fast-pdf-to-markdown/scripts/convert_pdf.py input.pdf \
  --output output.md \
  --report output.report.json
```

The command runs locally and does not upload the PDF or perform OCR. `uv` resolves the pinned dependency in an isolated environment.

## Why use it

- Adds `<!-- Page N -->` anchors for page-aware search, chunking, and citations.
- Emits a JSON report that distinguishes `clean`, `review_required`, and `ocr_required` results.
- Flags tables, columns, encoding problems, low text coverage, and missing pages.
- Reuses a content-addressed cache only after digest and semantic validation.
- Reprocesses the source in strict mode instead of trusting cached quality metadata.

## Usage

For evidence-sensitive work, enable the strict quality gate:

```bash
uv run --with pdf-inspector==0.2.6 python ~/.claude/skills/fast-pdf-to-markdown/scripts/convert_pdf.py input.pdf \
  --output output.md \
  --report output.report.json \
  --strict
```

Exit codes:

| Code | Meaning |
|---:|---|
| `0` | Conversion completed and strict review is not blocking. |
| `1` | Conversion failed. |
| `2` | The input or arguments are invalid. |
| `3` | Markdown and report were written, but review or OCR is still required. |

Useful options:

- `--cache-dir PATH`: store validated cache entries in a project-specific directory.
- `--force`: bypass an otherwise valid cache entry.
- `--max-mb SIZE`: reject PDFs larger than the configured MiB limit.

## Interpret the report

- `clean`: suitable for search, summarization, and chunking; verify the original page for exact quotations.
- `review_required`: inspect the reported table, column, coverage, or page-count risks.
- `ocr_required`: render and OCR only the named pages.

The Markdown is a fast searchable index, not a replacement for the original PDF's layout, figures, or exact table structure.

## Test

```bash
cd ~/.claude/skills/fast-pdf-to-markdown && uv run --with pdf-inspector==0.2.6 python -m unittest discover -s tests -v
```

The suite covers page anchors, malformed input, cache reuse, corrupted-cache rebuilding, and the exact strict-mode contract.

## Project structure

```text
.
├── SKILL.md
├── agents/openai.yaml
├── scripts/
│   ├── cache_store.py
│   ├── convert_pdf.py
│   └── pdf_pipeline.py
└── tests/test_convert_pdf.py
```

## Safety and scope

- Process only PDFs you are authorized to access.
- Do not use this project to bypass DRM or access controls.
- Keep the original PDF as the source of truth.
- Visually verify pages flagged for tables or multiple columns.
- State explicitly when OCR or visual review has not been completed.

## License

Released under the [MIT License](LICENSE).
