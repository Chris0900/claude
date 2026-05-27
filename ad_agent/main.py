#!/usr/bin/env python3
"""
뉴케어 플러스 구수한맛 — 9월 인스타그램 캠페인 시뮬레이션 에이전트
"""
import os
import sys
import time

from ad_sim.simulator import MonteCarloSimulator
from ad_sim.agent import AdCampaignAgent
from ad_sim import display


def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("오류: ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.", file=sys.stderr)
        sys.exit(1)

    t0 = time.perf_counter()

    display.print_header()
    display.print_historical_table()

    display.console.print("[dim]몬테카를로 시뮬레이션 실행 중 (A/B 주별 크리에이티브 로테이션 모드)…[/dim]")
    sim = MonteCarloSimulator(n=10_000, seed=42)
    scenarios = sim.run_all()
    display.console.print("[dim]시뮬레이션 완료.[/dim]\n")

    display.print_simulation_results(scenarios)
    display.print_roas_distribution(scenarios)

    display.console.print("[dim]Claude API 호출 중 (가설 생성)…[/dim]")
    agent = AdCampaignAgent(api_key=api_key)
    hypothesis, recommendations = agent.run(scenarios)

    display.print_hypothesis(hypothesis)
    display.print_recommendations(recommendations)
    display.print_cache_stats(agent.cache_stats)
    display.print_footer(time.perf_counter() - t0)


if __name__ == "__main__":
    main()
