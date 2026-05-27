#!/usr/bin/env python3
"""OEM 계약서 리스크 검토 및 대안 생성 에이전트"""

import sys
import json
import argparse
from pathlib import Path

import anthropic
from pydantic import BaseModel


class RiskItem(BaseModel):
    section: str
    severity: str          # high | medium | low
    category: str          # legal | financial | operational | IP | compliance
    risk_description: str
    alternative_clause: str
    negotiation_tip: str


class ContractAnalysis(BaseModel):
    executive_summary: str
    overall_risk_level: str    # high | medium | low
    risks: list[RiskItem]
    negotiation_priorities: list[str]
    recommended_additions: list[str]


SYSTEM_PROMPT = """당신은 OEM(주문자 상표 부착 생산) 계약 전문 법률 컨설턴트입니다.
20년 이상의 경험을 가진 국제 통상법 전문가로, 한국 기업의 OEM 계약 협상을 전문으로 합니다.

계약서를 다음 관점에서 철저히 분석하세요:
1. 지적재산권(IP) 보호 - 기술 노출, 역설계, 상표 소유권
2. 품질 보증 및 하자 책임 - 기준, 검사권, 리콜 비용
3. 대금 조건 및 위약금 - 결제 조건, 지연 이자, 보증금
4. 독점성 및 경쟁 제한 - 배타적 공급, 비경쟁 조항
5. 해지 조건 및 효과 - 해지 사유, 통지 기간, 후속 의무
6. 책임 한도 및 면책 - 손해배상 상한, 간접 손해 제외
7. 규정 준수 - 수출입 규제, 환경/안전 기준
8. 공급 의무 - MOQ, 납기, 재고 의무

각 리스크에 대해 반드시 구체적인 대안 조항을 한국어와 영어로 제시하고,
실질적인 협상 전략과 우선순위를 명확히 하세요."""


SEVERITY_CONFIG = {
    "high": ("🔴", "고위험"),
    "medium": ("🟡", "중위험"),
    "low": ("🟢", "저위험"),
}

CATEGORY_LABELS = {
    "legal": "법적",
    "financial": "재무",
    "operational": "운영",
    "IP": "지적재산",
    "compliance": "규정준수",
}


def analyze_contract(contract_text: str, client: anthropic.Anthropic) -> ContractAnalysis | None:
    """계약서를 분석하여 구조화된 결과 반환"""
    print("🔍 계약서 심층 분석 중... (1-2분 소요될 수 있습니다)\n")
    response = client.messages.parse(
        model="claude-opus-4-7",
        max_tokens=8192,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"다음 OEM 계약서를 분석하고 리스크와 대안을 제시해주세요:\n\n{contract_text}"
        }],
        output_format=ContractAnalysis,
    )
    return response.parsed_output


def display_analysis(analysis: ContractAnalysis) -> None:
    """분석 결과를 포맷하여 출력"""
    overall_icon, overall_label = SEVERITY_CONFIG.get(
        analysis.overall_risk_level, ("⚪", "미정")
    )

    print("=" * 70)
    print("📋 OEM 계약서 리스크 분석 보고서")
    print("=" * 70)

    print(f"\n[총괄 위험도] {overall_icon} {overall_label.upper()}\n")
    print("【요약】")
    print(analysis.executive_summary)

    print(f"\n{'─' * 70}")
    print(f"📊 리스크 항목 ({len(analysis.risks)}개 발견)")
    print(f"{'─' * 70}")

    for i, risk in enumerate(analysis.risks, 1):
        icon, label = SEVERITY_CONFIG.get(risk.severity, ("⚪", "미정"))
        cat_label = CATEGORY_LABELS.get(risk.category, risk.category)
        print(f"\n[{i}] {icon} {label} | {cat_label} | 조항: {risk.section}")
        print(f"    ⚠  리스크: {risk.risk_description}")
        print(f"    ✏  대안 조항:")
        for line in risk.alternative_clause.splitlines():
            print(f"        {line}")
        print(f"    💡 협상 전략: {risk.negotiation_tip}")

    print(f"\n{'─' * 70}")
    print("🎯 협상 우선순위")
    print(f"{'─' * 70}")
    for i, priority in enumerate(analysis.negotiation_priorities, 1):
        print(f"  {i}. {priority}")

    print(f"\n{'─' * 70}")
    print("➕ 추가 권고 조항")
    print(f"{'─' * 70}")
    for item in analysis.recommended_additions:
        print(f"  • {item}")

    print(f"\n{'=' * 70}\n")


def interactive_mode(
    contract_text: str, analysis: ContractAnalysis, client: anthropic.Anthropic
) -> None:
    """대화형 후속 질문 모드 (스트리밍)"""
    print("💬 대화형 질문 모드 시작 (종료: quit / 종료 / q)")
    print("   분석 결과에 대해 자유롭게 질문하세요.\n")

    summary_json = analysis.model_dump_json(indent=2)
    messages: list[dict] = [
        {
            "role": "user",
            "content": (
                f"다음은 OEM 계약서 원문과 초기 분석 결과입니다.\n\n"
                f"[계약서 원문]\n{contract_text}\n\n"
                f"[분석 결과 JSON]\n{summary_json}"
            ),
        },
        {
            "role": "assistant",
            "content": "계약서 분석이 완료되었습니다. 특정 조항이나 리스크에 대해 더 자세히 알고 싶으신 점을 질문해 주세요.",
        },
    ]

    while True:
        try:
            user_input = input("\n질문: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n분석을 종료합니다.")
            break

        if not user_input or user_input.lower() in ("quit", "exit", "종료", "q"):
            print("분석을 종료합니다.")
            break

        messages.append({"role": "user", "content": user_input})

        print("\n답변: ", end="", flush=True)
        full_response = ""
        with client.messages.stream(
            model="claude-opus-4-7",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                print(text, end="", flush=True)
                full_response += text
        print()

        messages.append({"role": "assistant", "content": full_response})


def read_contract_text(args: argparse.Namespace) -> str:
    if args.contract_file:
        path = Path(args.contract_file)
        if not path.exists():
            print(f"오류: 파일을 찾을 수 없습니다 — {args.contract_file}", file=sys.stderr)
            sys.exit(1)
        return path.read_text(encoding="utf-8")

    if not sys.stdin.isatty():
        return sys.stdin.read()

    print("계약서 텍스트를 입력하세요 (입력 완료 후 Ctrl+D):")
    return sys.stdin.read()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="OEM 계약서 리스크 검토 및 대안 생성 에이전트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""사용 예시:
  python oem_contract_agent.py contract.txt
  python oem_contract_agent.py contract.txt --interactive
  python oem_contract_agent.py contract.txt --output result.json
  cat contract.txt | python oem_contract_agent.py
""",
    )
    parser.add_argument("contract_file", nargs="?", help="계약서 파일 경로 (미입력 시 stdin)")
    parser.add_argument("-i", "--interactive", action="store_true", help="분석 후 대화형 Q&A 모드 진입")
    parser.add_argument("--output", metavar="FILE", help="분석 결과를 JSON 파일로 저장")
    args = parser.parse_args()

    contract_text = read_contract_text(args)
    if not contract_text.strip():
        print("오류: 계약서 내용이 비어 있습니다.", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic()

    analysis = analyze_contract(contract_text, client)
    if analysis is None:
        print("오류: 계약서 분석에 실패했습니다.", file=sys.stderr)
        sys.exit(1)

    display_analysis(analysis)

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(analysis.model_dump_json(indent=2), encoding="utf-8")
        print(f"✅ 분석 결과가 저장되었습니다: {args.output}")

    if args.interactive:
        interactive_mode(contract_text, analysis, client)


if __name__ == "__main__":
    main()
