[English](README.md) · [한국어](README.ko.md)

# Fast PDF to Markdown

허가받은 PDF를 검색 가능한 페이지 앵커 Markdown으로 변환하고, 추출 위험을 보고하며, 검증된 결과를 캐시해 반복 작업을 빠르게 만드는 로컬 Claude Code 스킬입니다.

## 빠른 시작

한 줄로 스킬을 설치합니다.

```bash
git clone https://github.com/NewTurn2017/fast-pdf-to-markdown.git ~/.claude/skills/fast-pdf-to-markdown
```

고정된 `pdf-inspector` 런타임으로 PDF를 변환합니다.

```bash
uv run --with pdf-inspector==0.2.6 python ~/.claude/skills/fast-pdf-to-markdown/scripts/convert_pdf.py input.pdf \
  --output output.md \
  --report output.report.json
```

이 명령은 로컬에서 실행되며 PDF를 업로드하거나 OCR을 수행하지 않습니다. `uv`는 고정된 의존성을 격리 환경에서 준비합니다.

## 주요 특징

- 페이지 단위 검색·청킹·인용을 위한 `<!-- Page N -->` 앵커를 추가합니다.
- `clean`, `review_required`, `ocr_required`를 구분하는 JSON 보고서를 생성합니다.
- 표, 다단, 인코딩 문제, 낮은 텍스트 커버리지, 누락 페이지를 표시합니다.
- 다이제스트와 의미 검증을 통과한 콘텐츠 주소형 캐시만 재사용합니다.
- strict 모드에서는 캐시된 품질 메타데이터를 신뢰하지 않고 원본을 다시 처리합니다.

## 사용법

근거가 중요한 작업에는 strict 품질 게이트를 사용합니다.

```bash
uv run --with pdf-inspector==0.2.6 python ~/.claude/skills/fast-pdf-to-markdown/scripts/convert_pdf.py input.pdf \
  --output output.md \
  --report output.report.json \
  --strict
```

종료 코드:

| 코드 | 의미 |
|---:|---|
| `0` | 변환이 완료됐고 strict 검토가 차단하지 않습니다. |
| `1` | 변환에 실패했습니다. |
| `2` | 입력 또는 인자가 잘못됐습니다. |
| `3` | Markdown과 보고서는 생성됐지만 검토 또는 OCR이 필요합니다. |

주요 옵션:

- `--cache-dir PATH`: 검증된 캐시를 프로젝트별 디렉터리에 저장합니다.
- `--force`: 유효한 캐시가 있어도 사용하지 않습니다.
- `--max-mb SIZE`: 설정한 MiB보다 큰 PDF를 거부합니다.

## 보고서 해석

- `clean`: 검색·요약·청킹에 사용할 수 있으며, 정확한 인용은 원본 페이지를 확인합니다.
- `review_required`: 보고된 표·다단·커버리지·페이지 수 위험을 확인합니다.
- `ocr_required`: 지정된 페이지만 렌더링하고 OCR합니다.

생성된 Markdown은 빠른 검색 인덱스이며 원본 PDF의 레이아웃·그림·정확한 표 구조를 대체하지 않습니다.

## 테스트

```bash
cd ~/.claude/skills/fast-pdf-to-markdown && uv run --with pdf-inspector==0.2.6 python -m unittest discover -s tests -v
```

테스트는 페이지 앵커, 잘못된 입력, 캐시 재사용, 손상된 캐시 재생성, 정확한 strict 모드 계약을 검증합니다.

## 프로젝트 구조

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

## 안전 및 범위

- 접근 권한이 있는 PDF만 처리합니다.
- DRM이나 접근 통제를 우회하는 용도로 사용하지 않습니다.
- 원본 PDF를 최종 근거로 보존합니다.
- 표 또는 다단으로 표시된 페이지를 시각적으로 검증합니다.
- OCR 또는 시각 검토를 완료하지 않았다면 명확히 밝힙니다.

## 라이선스

[MIT License](LICENSE)로 배포됩니다.
