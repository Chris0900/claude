from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich import box
from rich.text import Text

from .models import SimulationResult, ScenarioResult
from .historical_data import SCENARIOS

console = Console()

SCENARIO_LABELS = {
    "optimistic": ("낙관", "bright_green"),
    "base":       ("기준", "bright_yellow"),
    "pessimistic": ("비관", "bright_red"),
}


def print_header() -> None:
    console.print(Panel(
        "[bold cyan]뉴케어 플러스 구수한맛 — 9월 인스타그램 캠페인 시뮬레이션 리포트[/bold cyan]\n"
        "[dim]일본 코스트코 × 마이크로 인플루언서 | 몬테카를로 10,000회[/dim]",
        box=box.DOUBLE,
        expand=True,
    ))


def print_historical_table() -> None:
    table = Table(title="📊 3개월 실제 성과 요약", box=box.ROUNDED, show_header=True)
    table.add_column("월", style="bold")
    table.add_column("콘텐츠", justify="right")
    table.add_column("총조회수", justify="right")
    table.add_column("CTR", justify="right")
    table.add_column("매장방문CVR", justify="right")
    table.add_column("온라인CVR", justify="right")
    table.add_column("온라인 판매", justify="right")
    table.add_column("광고비(원)", justify="right")

    rows = [
        ("6월", 15, 150_000, 0.020, 0.10, 0.08, 240, 2_100_000),
        ("7월",  8,  96_000, 0.020, 0.12, 0.10, 192, 1_344_000),
        ("8월",  8, 120_000, 0.030, 0.15, 0.10, 360, 1_680_000),
    ]
    for month, cnt, views, ctr, vcvr, ocvr, sales, spend in rows:
        ad_spend = views / 1_000 * 14_000
        table.add_row(
            month,
            str(cnt),
            f"{views:,}",
            f"{ctr:.1%}",
            f"{vcvr:.1%}",
            f"{ocvr:.1%}",
            str(sales),
            f"{ad_spend:,.0f}",
        )
    console.print(table)
    console.print()


def print_simulation_results(results: list[ScenarioResult]) -> None:
    table = Table(title="🎲 시뮬레이션 결과 요약 (P10 / P50 / P90)", box=box.ROUNDED)
    table.add_column("시나리오", style="bold")
    table.add_column("인플루언서", justify="right")
    table.add_column("예산(원)", justify="right")
    table.add_column("온라인 판매\nP10/P50/P90", justify="right")
    table.add_column("추정매출 P50(원)", justify="right")
    table.add_column("ROAS P50", justify="right")
    table.add_column("ROAS>1 확률", justify="right")

    for r in results:
        label, color = SCENARIO_LABELS[r.scenario]
        cfg = SCENARIOS[r.scenario]
        sim = r.simulation
        table.add_row(
            f"[{color}]{label}[/{color}]",
            str(cfg["content_count"]),
            f"{cfg['budget_krw']:,}",
            (
                f"{sim.online_sales.p10:.0f} / "
                f"{sim.online_sales.p50:.0f} / "
                f"{sim.online_sales.p90:.0f}"
            ),
            f"{sim.estimated_revenue_krw.p50:,.0f}",
            f"{sim.roas.p50:.2f}x",
            f"{sim.prob_roas_gt1:.1%}",
        )
    console.print(table)
    console.print()


def print_roas_distribution(results: list[ScenarioResult]) -> None:
    table = Table(title="📈 ROAS 분포 (P10 / P25 / P50 / P75 / P90)", box=box.ROUNDED)
    table.add_column("시나리오", style="bold")
    table.add_column("P10", justify="right")
    table.add_column("P25", justify="right")
    table.add_column("P50", justify="right")
    table.add_column("P75", justify="right")
    table.add_column("P90", justify="right")

    for r in results:
        label, color = SCENARIO_LABELS[r.scenario]
        roas = r.simulation.roas

        def fmt(v: float) -> str:
            if v >= 3.0:
                return f"[bright_green]{v:.2f}x[/bright_green]"
            elif v >= 2.0:
                return f"[yellow]{v:.2f}x[/yellow]"
            elif v >= 1.0:
                return f"[orange1]{v:.2f}x[/orange1]"
            else:
                return f"[red]{v:.2f}x[/red]"

        table.add_row(
            f"[{color}]{label}[/{color}]",
            fmt(roas.p10), fmt(roas.p25), fmt(roas.p50), fmt(roas.p75), fmt(roas.p90),
        )
    console.print(table)
    console.print()


def print_hypothesis(text: str) -> None:
    console.print(Panel(
        text,
        title="[bold blue]🤔 시뮬레이션 전 가설[/bold blue]",
        box=box.ROUNDED,
        padding=(1, 2),
    ))
    console.print()


def print_recommendations(text: str) -> None:
    console.print(Panel(
        text,
        title="[bold green]✅ 9월 캠페인 실행 권고안[/bold green]",
        box=box.ROUNDED,
        padding=(1, 2),
    ))
    console.print()


def print_cache_stats(stats: dict[str, int]) -> None:
    created = stats.get("created", 0)
    read = stats.get("read", 0)
    console.print(
        f"[dim]프롬프트 캐시 — 생성: {created:,} 토큰 | 히트: {read:,} 토큰[/dim]"
    )
    console.print()


def print_footer(elapsed: float) -> None:
    console.print(f"[dim]실행 시간: {elapsed:.1f}초[/dim]")
