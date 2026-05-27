import math
import random
import statistics
from typing import Optional

from .models import MetricStats, SimulationResult, ScenarioResult, CampaignParams
from .historical_data import SCENARIOS, PRODUCT_PRICE_KRW, STORE_PURCHASE_RATE

CPM = 14_000  # KRW, 고정
WEEKS = 4

# 인게이지먼트 분포 (Meta 파트너십 광고 기준 ~6%)
_ENG_MEAN = 0.06
_ENG_STD = 0.015


class MonteCarloSimulator:
    def __init__(self, n: int = 10_000, seed: Optional[int] = None):
        self.n = n
        self.rng = random.Random(seed)

    def _lognormal_sample(self, mean: float, std: float) -> float:
        sigma2 = math.log(1 + (std / mean) ** 2)
        mu = math.log(mean) - sigma2 / 2
        return math.exp(self.rng.gauss(mu, math.sqrt(sigma2)))

    def _beta_sample(self, mean: float, std: float) -> float:
        variance = std ** 2
        common = mean * (1 - mean) / variance - 1
        alpha = max(mean * common, 0.5)
        beta = max((1 - mean) * common, 0.5)
        return self.rng.betavariate(alpha, beta)

    def _stats(self, vals: list) -> MetricStats:
        s = sorted(vals)
        n = len(s)
        return MetricStats(
            mean=statistics.mean(vals),
            std=statistics.stdev(vals),
            p10=s[int(n * 0.10)],
            p25=s[int(n * 0.25)],
            p50=s[int(n * 0.50)],
            p75=s[int(n * 0.75)],
            p90=s[int(n * 0.90)],
            ci_lower=s[int(n * 0.05)],
            ci_upper=s[int(n * 0.95)],
        )

    def _kill_underperformers(
        self,
        pool: list[tuple[float, float]],
        high_eng_keep_pct: float,
    ) -> list[tuple[float, float]]:
        """
        A/B kill rules:
        1. 인게이지먼트 상위 high_eng_keep_pct → 무조건 유지
        2. 나머지 중 CTR >= 중간값 → 유지 (하위 ~50% 제거)
        3. 안전장치: 풀의 30% 미만으로는 절대 축소하지 않음
        """
        if len(pool) <= 2:
            return pool

        ctrs = [c[0] for c in pool]
        engs = [c[1] for c in pool]

        eng_threshold = sorted(engs)[int(len(engs) * (1 - high_eng_keep_pct))]
        median_ctr = sorted(ctrs)[len(ctrs) // 2]

        survivors = [
            c for c in pool
            if c[1] >= eng_threshold   # 인게이지먼트 상위 → 유지
            or c[0] >= median_ctr      # CTR 중간값 이상 → 유지
        ]

        min_pool = max(2, int(len(pool) * 0.30))
        if len(survivors) < min_pool:
            survivors = sorted(pool, key=lambda c: c[0], reverse=True)[:min_pool]

        return survivors

    def simulate_ab(self, scenario_key: str) -> SimulationResult:
        """
        주별 A/B 크리에이티브 로테이션 시뮬레이션.

        매주 new_content_per_week 개의 신규 소재를 투입하고,
        주 말마다 저성과 소재를 제거한다. 주간 예산은 활성 풀에
        균등 배분되므로 총 조회수는 예산에 자동으로 수렴한다.
        """
        cfg = SCENARIOS[scenario_key]
        new_per_week: int = cfg["new_content_per_week"]
        high_eng_keep_pct: float = cfg["high_eng_keep_pct"]

        # 주간 목표 노출 = 월 예산을 4주로 균등 배분
        weekly_impressions_budget = cfg["budget_krw"] / WEEKS / CPM * 1_000

        imp_l, clk_l, ctr_l = [], [], []
        vis_l, vis_cvr_l, onl_l, onl_cvr_l, rev_l, roas_l = [], [], [], [], [], []

        for _ in range(self.n):
            # CVR은 오디언스 특성 → 월 전체에서 1회 샘플
            visit_cvr = self._beta_sample(cfg["visit_cvr_mean"], cfg["visit_cvr_std"])
            online_cvr = self._beta_sample(cfg["online_cvr_mean"], cfg["online_cvr_std"])

            # 크리에이티브 풀: (ctr, engagement_rate)
            pool: list[tuple[float, float]] = []
            total_views = 0.0
            total_clicks = 0.0

            for week in range(WEEKS):
                # 신규 소재 투입
                for _ in range(new_per_week):
                    ctr = self._beta_sample(cfg["ctr_mean"], cfg["ctr_std"])
                    eng = self._beta_sample(_ENG_MEAN, _ENG_STD)
                    pool.append((ctr, eng))

                # 주간 예산을 활성 소재에 균등 배분 → 조회수 결정
                views_each_mean = weekly_impressions_budget / len(pool)
                views_each_std = views_each_mean * 0.30

                for (ctr, _) in pool:
                    v = max(1.0, self._lognormal_sample(views_each_mean, views_each_std))
                    total_views += v
                    total_clicks += v * ctr

                # 마지막 주는 kill 없이 모두 소진
                if week < WEEKS - 1:
                    pool = self._kill_underperformers(pool, high_eng_keep_pct)

            store_visits = total_clicks * visit_cvr
            store_purchases = store_visits * STORE_PURCHASE_RATE
            online_sales = total_clicks * online_cvr
            revenue = (online_sales + store_purchases) * PRODUCT_PRICE_KRW
            ad_spend = (total_views / 1_000) * CPM
            roas = revenue / max(ad_spend, 1)

            imp_l.append(total_views)
            clk_l.append(total_clicks)
            ctr_l.append(total_clicks / max(total_views, 1))
            vis_l.append(store_visits)
            vis_cvr_l.append(visit_cvr)
            onl_l.append(online_sales)
            onl_cvr_l.append(online_cvr)
            rev_l.append(revenue)
            roas_l.append(roas)

        base_median = self._stats(onl_l).p50
        return SimulationResult(
            impressions=self._stats(imp_l),
            clicks=self._stats(clk_l),
            ctr=self._stats(ctr_l),
            store_visits=self._stats(vis_l),
            online_sales=self._stats(onl_l),
            visit_cvr=self._stats(vis_cvr_l),
            online_cvr=self._stats(onl_cvr_l),
            estimated_revenue_krw=self._stats(rev_l),
            roas=self._stats(roas_l),
            prob_exceed_base=sum(1 for v in onl_l if v > base_median) / self.n,
            prob_roas_gt1=sum(1 for v in roas_l if v > 1.0) / self.n,
            n_simulations=self.n,
        )

    def run_all(self) -> list[ScenarioResult]:
        return [
            ScenarioResult(scenario=k, simulation=self.simulate_ab(k))
            for k in ["optimistic", "base", "pessimistic"]
        ]
