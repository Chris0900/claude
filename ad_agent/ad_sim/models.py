from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class HistoricalData:
    month: str
    views_per_content: int
    content_count: int
    total_views: int
    clicks: int
    ctr: float          # e.g. 0.02
    cpm: int            # KRW
    store_visits: int
    visit_cvr: float    # store visit conversion rate
    online_sales: int
    online_cvr: float


@dataclass
class CampaignParams:
    campaign_name: str
    platform: str
    monthly_budget_krw: int
    duration_days: int
    creative_type: str
    audience_type: str
    product_price_krw: int      # avg product price in KRW
    objective: str
    target_month: str
    content_count_planned: int


@dataclass
class MetricStats:
    mean: float
    std: float
    p10: float
    p25: float
    p50: float
    p75: float
    p90: float
    ci_lower: float     # P5
    ci_upper: float     # P95


@dataclass
class SimulationResult:
    impressions: MetricStats
    clicks: MetricStats
    ctr: MetricStats
    store_visits: MetricStats
    online_sales: MetricStats
    visit_cvr: MetricStats
    online_cvr: MetricStats
    estimated_revenue_krw: MetricStats
    roas: MetricStats
    prob_exceed_base: float     # P(online_sales > base scenario median)
    prob_roas_gt1: float        # P(ROAS > 1.0)
    n_simulations: int


@dataclass
class ScenarioResult:
    scenario: str           # optimistic | base | pessimistic
    simulation: SimulationResult


@dataclass
class PerformanceReport:
    campaign_params: CampaignParams
    historical_summary: str
    hypothesis: str
    scenarios: List[ScenarioResult]
    recommendations: str
    cache_stats: Dict[str, int]
    execution_time_seconds: float
