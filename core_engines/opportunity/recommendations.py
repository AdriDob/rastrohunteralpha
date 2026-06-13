"""Recommendations engine — generates advisory opportunity lists.

All recommendations are advisory only. Never modifies pipeline data.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List

from core.opportunity.models import Opportunity, OpportunityRecommendations

logger = logging.getLogger("rastro.opportunity.recommendations")


def generate_recommendations(opportunities: List[Opportunity]) -> OpportunityRecommendations:
    """Generate advisory recommendation lists from scored opportunities.

    Categories:
      - Top Opportunities: highest overall score
      - Top Independent: highest-scoring independent programs
      - Top Web3: highest-scoring web3 opportunities
      - Fast ROI: high reward + high tech overlap + low competition
      - Long Term: high scope + high freshness, lower urgency
      - Low Competition: lowest competition scores with decent reward
    """
    scored = [o for o in opportunities if o.score is not None]
    if not scored:
        return OpportunityRecommendations(generated_at="", summary="No scored opportunities available.")

    now = datetime.now(timezone.utc).isoformat()

    # Sort by overall score descending
    sorted_by_score = sorted(scored, key=lambda o: o.score.overall, reverse=True)

    # Top 10 overall
    top_all = sorted_by_score[:10]

    # Category filtered
    independent = sorted(
        [o for o in scored if o.category == "independent"],
        key=lambda o: o.score.overall, reverse=True,
    )[:5]

    web3 = sorted(
        [o for o in scored if o.category == "web3"],
        key=lambda o: o.score.overall, reverse=True,
    )[:5]

    # Fast ROI: reward > 0.5 AND tech overlap > 0.3 AND competition > 0.4
    fast_roi_candidates = [
        o for o in scored
        if o.score.reward_potential > 0.5
        and o.score.technology_overlap > 0.3
        and o.score.competition_estimate > 0.4
    ]
    fast_roi = sorted(fast_roi_candidates, key=lambda o: o.score.reward_potential, reverse=True)[:5]

    # Long term: scope > 0.4 AND freshness > 0.3 but not in top 10
    long_term_candidates = [
        o for o in scored
        if o.score.scope_quality > 0.4
        and o.score.freshness > 0.3
        and o not in top_all
    ]
    long_term = sorted(long_term_candidates, key=lambda o: o.score.scope_quality, reverse=True)[:5]

    # Low competition: competition > 0.6 AND overall > 0.3
    low_comp_candidates = [
        o for o in scored
        if o.score.competition_estimate > 0.6
        and o.score.overall > 0.3
    ]
    low_competition = sorted(low_comp_candidates, key=lambda o: o.score.overall, reverse=True)[:5]

    # Summary
    total = len(scored)
    summary_parts = []
    if top_all:
        summary_parts.append(f"Top opportunity: {top_all[0].name} (score {top_all[0].score.overall:.2f})")
    if fast_roi:
        summary_parts.append(f"Fast ROI: {len(fast_roi)} opportunities identified")
    if low_competition:
        summary_parts.append(f"Low competition: {len(low_competition)} opportunities")
    summary_parts.append(f"{total} total opportunities scored")

    return OpportunityRecommendations(
        top_opportunities=top_all,
        top_independent=independent,
        top_web3=web3,
        fast_roi=fast_roi,
        long_term=long_term,
        low_competition=low_competition,
        generated_at=now,
        summary=" | ".join(summary_parts),
    )
