import math
import random
import statistics
from typing import Optional

from .models import MetricStats, SimulationResult, ScenarioResult, CampaignParams
from .historical_data import SCENARIOS, PRODUCT_PRICE_KRW, STORE_PURCHASE_RATE


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

    def simulate(self, scenario_key: str) -> SimulationResult:
        cfg = SCENARIOS[scenario_key]
        cpm = 14_000  # KRW, 고정

        imp_l, clk_l, ctr_l = [], [], []
        vis_l, vis_cvr_l = [], []
        onl_l, onl_cvr_l = [], []
        rev_l, roas_l = [], []

        for _ in range(self.n):
            total_views = sum(
                max(1, self._lognormal_sample(
                    cfg["views_per_content_mean"],
                    cfg["views_per_content_std"],
                ))
                for _ in range(cfg["content_count"])
            )

            ctr = self._beta_sample(cfg["ctr_mean"], cfg["ctr_std"])
            visit_cvr = self._beta_sample(cfg["visit_cvr_mean"], cfg["visit_cvr_std"])
            online_cvr = self._beta_sample(cfg["online_cvr_mean"], cfg["online_cvr_std"])

            clicks = total_views * ctr
            store_visits = clicks * visit_cvr
            store_purchases = store_visits * STORE_PURCHASE_RATE
            online_sales = clicks * online_cvr

            revenue = (online_sales + store_purchases) * PRODUCT_PRICE_KRW
            ad_spend = (total_views / 1_000) * cpm
            roas = revenue / max(ad_spend, 1)

            imp_l.append(total_views)
            clk_l.append(clicks)
            ctr_l.append(ctr)
            vis_l.append(store_visits)
            vis_cvr_l.append(visit_cvr)
            onl_l.append(online_sales)
            onl_cvr_l.append(online_cvr)
            rev_l.append(revenue)
            roas_l.append(roas)

        base_online_median = self._stats(onl_l).p50

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
            prob_exceed_base=sum(1 for v in onl_l if v > base_online_median) / self.n,
            prob_roas_gt1=sum(1 for v in roas_l if v > 1.0) / self.n,
            n_simulations=self.n,
        )

    def run_all(self) -> list[ScenarioResult]:
        return [
            ScenarioResult(scenario=k, simulation=self.simulate(k))
            for k in ["optimistic", "base", "pessimistic"]
        ]
