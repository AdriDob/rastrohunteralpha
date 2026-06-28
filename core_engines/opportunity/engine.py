"""OpportunityEngine — main entry point for the Opportunity Intelligence Layer.

Coordinates discovery, scoring, recommendations, and history.
Read-only. Never modifies pipeline data.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from core_engines.observability import record, timer
from core_engines.opportunity.history import get_history_manager
from core_engines.opportunity.models import (
    EVHRating,
    IdentityVaultEntry,
    Opportunity,
    OpportunityProviderInfo,
    OpportunityRecommendations,
    OpportunitySnapshot,
)
from core_engines.opportunity.providers import get_providers
from core_engines.opportunity.recommendations import generate_recommendations
from core_engines.opportunity.scoring import score_opportunity as score_legacy
from core_engines.opportunity.scoring2 import (
    _score_to_priority,
    compute_layered_score,
)

logger = logging.getLogger("rastro.opportunity.engine")

_GLOBAL_ENGINE: OpportunityEngine | None = None


class OpportunityEngine:
    """Coordinates the full opportunity intelligence pipeline."""

    def __init__(self) -> None:
        self._opportunities: dict[str, Opportunity] = {}
        self._provider_info: dict[str, OpportunityProviderInfo] = {}
        self._last_refresh: str | None = None
        self._history = get_history_manager()
        self._recommendations: OpportunityRecommendations | None = None
        self._identity_vault: dict[str, IdentityVaultEntry] = {}

    # ── Discovery ───────────────────────────────────────────────────

    def discover_all(self, use_layered_scoring: bool = True) -> list[Opportunity]:
        """Run discovery on all registered providers and score results."""
        all_opps: list[Opportunity] = []
        for provider in get_providers():
            with timer(f"opportunity.provider.{provider.name}.discover"):
                try:
                    discovered = provider.discover()
                    all_opps.extend(discovered)
                    info = provider.info()
                    self._provider_info[provider.name] = OpportunityProviderInfo(
                        name=info.name,
                        category=info.category,
                        active=info.active,
                        opportunity_count=info.opportunity_count,
                        last_refresh=info.last_refresh,
                        health_status="healthy",
                    )
                    logger.info("Provider %s discovered %d opportunities", provider.name, len(discovered))
                except Exception as exc:
                    logger.warning("Provider %s discovery failed: %s", provider.name, exc)
                    self._provider_info[provider.name] = OpportunityProviderInfo(
                        name=provider.name,
                        category=getattr(provider, "category", "unknown"),
                        active=False,
                        opportunity_count=0,
                        health_status="down",
                    )

        scored = self._score_all(all_opps, use_layered_scoring)

        self._opportunities = {o.id: o for o in scored}
        self._last_refresh = datetime.now(timezone.utc).isoformat()

        record("opportunity.discover.count", len(scored))
        record("opportunity.providers.active", len(get_providers()))

        return scored

    def refresh(self, use_layered_scoring: bool = True) -> list[Opportunity]:
        """Incremental refresh — checks for updates from providers."""
        updated: list[Opportunity] = []
        for provider in get_providers():
            with timer(f"opportunity.provider.{provider.name}.refresh"):
                try:
                    refreshed = provider.refresh()
                    for r in refreshed:
                        s = compute_layered_score(r) if use_layered_scoring else score_legacy(r)
                        priority = _score_to_priority(s.overall)
                        r_with_score = Opportunity(
                            id=r.id, name=r.name, source=r.source,
                            category=r.category, subcategory=r.subcategory,
                            public_url=r.public_url, scope_summary=r.scope_summary,
                            reward_info=r.reward_info, technology_tags=r.technology_tags,
                            last_update=r.last_update, confidence=r.confidence,
                            metadata=r.metadata, score=s, priority=priority,
                            created_at=r.created_at, estimated_payout=r.estimated_payout,
                            estimated_effort_hours=r.estimated_effort_hours,
                            has_rewards=r.has_rewards,
                        )
                        self._opportunities[r.id] = r_with_score
                        updated.append(r_with_score)
                    info = provider.info()
                    self._provider_info[provider.name] = OpportunityProviderInfo(
                        name=info.name, category=info.category, active=True,
                        opportunity_count=info.opportunity_count,
                        last_refresh=info.last_refresh, health_status="healthy",
                    )
                except Exception as exc:
                    logger.warning("Provider %s refresh failed: %s", provider.name, exc)
                    self._provider_info[provider.name] = OpportunityProviderInfo(
                        name=provider.name,
                        category=getattr(provider, "category", "unknown"),
                        active=False,
                        opportunity_count=0,
                        health_status="degraded",
                    )

        self._last_refresh = datetime.now(timezone.utc).isoformat()
        return updated

    def _score_all(self, opps: list[Opportunity], use_layered: bool) -> list[Opportunity]:
        scored: list[Opportunity] = []
        for opp in opps:
            with timer("opportunity.score"):
                try:
                    s = compute_layered_score(opp) if use_layered else score_legacy(opp)
                    priority = _score_to_priority(s.overall)
                    scored.append(Opportunity(
                        id=opp.id, name=opp.name, source=opp.source,
                        category=opp.category, subcategory=opp.subcategory,
                        public_url=opp.public_url, scope_summary=opp.scope_summary,
                        reward_info=opp.reward_info, technology_tags=opp.technology_tags,
                        last_update=opp.last_update, confidence=opp.confidence,
                        metadata=opp.metadata, score=s, priority=priority,
                        created_at=opp.created_at, estimated_payout=opp.estimated_payout,
                        estimated_effort_hours=opp.estimated_effort_hours,
                        has_rewards=opp.has_rewards,
                    ))
                except Exception as exc:
                    logger.warning("Scoring failed for %s: %s", opp.id, exc)
                    scored.append(opp)
        return scored

    # ── EVH ─────────────────────────────────────────────────────────

    def get_evh_rankings(self, limit: int = 20) -> list[Opportunity]:
        """Return opportunities ranked by EVH descending."""
        sorted_opps = sorted(
            [o for o in self._opportunities.values() if o.score and o.score.evh],
            key=lambda o: o.score.evh.value if o.score.evh else 0,
            reverse=True,
        )
        return sorted_opps[:limit]

    def get_evh_summary(self) -> dict[str, Any]:
        """Return EVH distribution summary."""
        evh_list = [o.score.evh for o in self._opportunities.values() if o.score and o.score.evh]
        if not evh_list:
            return {"high": 0, "medium": 0, "low": 0, "average_evh": 0.0}

        high = sum(1 for e in evh_list if e.rating == EVHRating.high)
        medium = sum(1 for e in evh_list if e.rating == EVHRating.medium)
        low = sum(1 for e in evh_list if e.rating == EVHRating.low)
        avg = sum(e.value for e in evh_list) / max(len(evh_list), 1)

        return {"high": high, "medium": medium, "low": low, "average_evh": round(avg, 2)}

    # ── Identity Vault ──────────────────────────────────────────────

    def get_identity_vault(self) -> dict[str, IdentityVaultEntry]:
        return dict(self._identity_vault)

    def set_identity_entry(self, entry: IdentityVaultEntry) -> None:
        self._identity_vault[entry.provider_name] = entry

    def remove_identity_entry(self, provider_name: str) -> None:
        self._identity_vault.pop(provider_name, None)

    # ── Accessors ───────────────────────────────────────────────────

    def get_all(self) -> list[Opportunity]:
        return sorted(
            self._opportunities.values(),
            key=lambda o: o.score.overall if o.score else 0,
            reverse=True,
        )

    def get_by_category(self, category: str) -> list[Opportunity]:
        return [o for o in self.get_all() if o.category == category]

    def get_by_priority(self, priority: str) -> list[Opportunity]:
        return [o for o in self.get_all() if o.priority == priority]

    def get_by_id(self, opp_id: str) -> Opportunity | None:
        return self._opportunities.get(opp_id)

    def get_providers_info(self) -> list[OpportunityProviderInfo]:
        return list(self._provider_info.values())

    def get_recommendations(self, force: bool = False) -> OpportunityRecommendations:
        if self._recommendations is None or force:
            all_opps = self.get_all()
            recs = generate_recommendations(all_opps)
            evh_ranked = self.get_evh_rankings(10)
            self._recommendations = OpportunityRecommendations(
                top_opportunities=recs.top_opportunities,
                top_independent=recs.top_independent,
                top_web3=recs.top_web3,
                fast_roi=recs.fast_roi,
                long_term=recs.long_term,
                low_competition=recs.low_competition,
                evh_ranked=evh_ranked,
                generated_at=recs.generated_at,
                summary=recs.summary,
            )
        return self._recommendations

    def get_metrics(self) -> dict[str, Any]:
        all_opps = self.get_all()
        scored = [o for o in all_opps if o.score is not None]
        avg_score = sum(s.score.overall for s in scored) / max(len(scored), 1) if scored else 0.0

        evh_rankings = self.get_evh_rankings(10)
        evh_top_avg = 0.0
        if evh_rankings:
            evh_values = [o.score.evh.value for o in evh_rankings if o.score and o.score.evh]
            evh_top_avg = sum(evh_values) / max(len(evh_values), 1) if evh_values else 0.0

        all_categories = set(o.category for o in all_opps)
        by_category = {cat: len(self.get_by_category(cat)) for cat in sorted(all_categories)}

        return {
            "opportunities_total": len(all_opps),
            "providers_active": sum(1 for p in self._provider_info.values() if p.active),
            "recommendations_generated": len(self._recommendations.top_opportunities) if self._recommendations else 0,
            "emerging_events": len(self.get_by_category("emerging")),
            "average_score": round(avg_score, 4),
            "average_evh_top10": round(evh_top_avg, 2),
            "last_refresh": self._last_refresh or "",
            "by_priority": {
                "critical": len(self.get_by_priority("critical")),
                "high": len(self.get_by_priority("high")),
                "medium": len(self.get_by_priority("medium")),
                "low": len(self.get_by_priority("low")),
            },
            "by_category": by_category,
            "evh_distribution": self.get_evh_summary(),
            "providers_health": {
                p.name: p.health_status for p in self._provider_info.values()
            },
        }

    # ── History ──────────────────────────────────────────────────────

    def take_snapshot(self, period: str = "daily") -> OpportunitySnapshot:
        all_opps = self.get_all()
        metrics = self.get_metrics()
        snapshot = self._history.store_snapshot(all_opps, period, metrics)
        return snapshot

    def get_history(self, period: str | None = None, limit: int = 30) -> list[OpportunitySnapshot]:
        return self._history.get_snapshots(period, limit)


def get_engine() -> OpportunityEngine:
    global _GLOBAL_ENGINE
    if _GLOBAL_ENGINE is None:
        _GLOBAL_ENGINE = OpportunityEngine()
        logger.info("OpportunityEngine initialised (v2 — layered scoring)")
    return _GLOBAL_ENGINE
