import time
from typing import Optional

import anthropic

from .models import SimulationResult, ScenarioResult
from .prompts import SYSTEM_PROMPT, HYPOTHESIS_TEMPLATE, RECOMMENDATION_TEMPLATE

MODEL = "claude-sonnet-4-6"


class AdCampaignAgent:
    def __init__(self, api_key: Optional[str] = None):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.cache_stats = {"created": 0, "read": 0}

    def _update_cache_stats(self, usage: anthropic.types.Usage) -> None:
        self.cache_stats["created"] += getattr(usage, "cache_creation_input_tokens", 0) or 0
        self.cache_stats["read"] += getattr(usage, "cache_read_input_tokens", 0) or 0

    def generate_hypothesis(self) -> str:
        response = self.client.messages.create(
            model=MODEL,
            max_tokens=1024,
            thinking={"type": "disabled"},
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {"role": "user", "content": HYPOTHESIS_TEMPLATE}
            ],
        )
        self._update_cache_stats(response.usage)
        return response.content[0].text

    def generate_recommendations(
        self,
        hypothesis: str,
        optimistic: SimulationResult,
        base: SimulationResult,
        pessimistic: SimulationResult,
    ) -> str:
        prompt = RECOMMENDATION_TEMPLATE.format(
            hypothesis=hypothesis,
            opt_online_p50=optimistic.online_sales.p50,
            opt_online_p10=optimistic.online_sales.p10,
            opt_online_p90=optimistic.online_sales.p90,
            opt_rev_p50=optimistic.estimated_revenue_krw.p50,
            opt_rev_p90=optimistic.estimated_revenue_krw.p90,
            opt_roas_p50=optimistic.roas.p50,
            opt_roas_p10=optimistic.roas.p10,
            opt_roas_p90=optimistic.roas.p90,
            base_online_p50=base.online_sales.p50,
            base_online_p10=base.online_sales.p10,
            base_online_p90=base.online_sales.p90,
            base_rev_p50=base.estimated_revenue_krw.p50,
            base_rev_p90=base.estimated_revenue_krw.p90,
            base_roas_p50=base.roas.p50,
            base_roas_p10=base.roas.p10,
            base_roas_p90=base.roas.p90,
            base_prob_roas_gt1=base.prob_roas_gt1,
            pess_online_p50=pessimistic.online_sales.p50,
            pess_online_p10=pessimistic.online_sales.p10,
            pess_online_p90=pessimistic.online_sales.p90,
            pess_rev_p50=pessimistic.estimated_revenue_krw.p50,
            pess_roas_p50=pessimistic.roas.p50,
        )

        response = self.client.messages.create(
            model=MODEL,
            max_tokens=2048,
            thinking={"type": "disabled"},
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {"role": "user", "content": HYPOTHESIS_TEMPLATE},
                {"role": "assistant", "content": hypothesis},
                {"role": "user", "content": prompt},
            ],
        )
        self._update_cache_stats(response.usage)
        return response.content[0].text

    def run(self, scenarios: list[ScenarioResult]) -> tuple[str, str]:
        scenario_map = {r.scenario: r.simulation for r in scenarios}
        optimistic = scenario_map["optimistic"]
        base = scenario_map["base"]
        pessimistic = scenario_map["pessimistic"]

        hypothesis = self.generate_hypothesis()
        recommendations = self.generate_recommendations(
            hypothesis, optimistic, base, pessimistic
        )
        return hypothesis, recommendations
