"""
discovery.engine — Discovery Engine.

Consume feeds públicos de bug bounty, categoriza programas por
potencial de pago, complejidad tecnológica y densidad histórica.

Integraciones:
  - HackerOne, Bugcrowd, Intigriti, YesWeHack
  - GitHub Security Advisories
  - Web3 / Crypto bounty feeds
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.targets.hunter import Hunter
from core.engine.roi_model import apply_roi_to_priority

LOG = logging.getLogger("rastro.discovery")


@dataclass
class BountyProgram:
    id: int = 0
    name: str = ""
    platform: str = ""
    domain: Optional[str] = None
    program_url: Optional[str] = None
    payout_range: str = ""
    tech_stack: List[str] = field(default_factory=list)
    is_web3: bool = False
    is_api: bool = False
    scope_count: int = 0
    opportunity_score: float = 0.0
    roi_score: float = 0.0
    competition_score: float = 0.0
    freshness_score: float = 0.0
    tags: List[str] = field(default_factory=list)


@dataclass
class ProgramRanking:
    programs: List[BountyProgram] = field(default_factory=list)
    total_programs: int = 0
    avg_roi: float = 0.0
    top_category: str = ""
    web3_count: int = 0
    api_count: int = 0

    @property
    def top_programs(self) -> List[BountyProgram]:
        return sorted(self.programs, key=lambda p: p.roi_score, reverse=True)[:10]


class DiscoveryEngine:
    """Motor de descubrimiento de programas bug bounty."""

    def __init__(self):
        self._hunter = Hunter()

    def fetch_all(self, limit: int = 50) -> ProgramRanking:
        """Obtiene y clasifica programas de todas las plataformas."""
        all_programs: List[BountyProgram] = []

        for platform in Hunter.SUPPORTED_PLATFORMS:
            try:
                raw = self._hunter.fetch_public_programs(platform, limit=limit)
                ingested = self._hunter.ingest_programs(raw)
                for p in ingested:
                    scores = p.get("scores", {})
                    bp = BountyProgram(
                        id=p.get("id", 0),
                        name=p.get("name", ""),
                        platform=platform,
                        domain=str(p.get("domain")) if p.get("domain") else None,
                        opportunity_score=scores.get("opportunity_score", 0.0),
                        roi_score=scores.get("roi_score", 0.0),
                        competition_score=scores.get("competition_score", 0.0),
                        freshness_score=scores.get("freshness_score", 0.0),
                    )
                    # Categorización automática
                    bp.is_web3 = any(kw in bp.name.lower() for kw in {"web3", "crypto", "wallet", "defi", "nft", "blockchain"})
                    bp.is_api = "api" in bp.name.lower() or bool(scores.get("attack_surface_score", 0) > 50)
                    all_programs.append(bp)
            except Exception as exc:
                LOG.warning("Error fetching %s: %s", platform, exc)

        all_programs.sort(key=lambda p: p.roi_score, reverse=True)

        web3_count = sum(1 for p in all_programs if p.is_web3)
        api_count = sum(1 for p in all_programs if p.is_api)
        avg_roi = sum(p.roi_score for p in all_programs) / max(len(all_programs), 1)

        # Categoría dominante
        categories = {"web2": 0, "web3": web3_count, "api": api_count}
        top_cat = max(categories, key=categories.get)

        return ProgramRanking(
            programs=all_programs,
            total_programs=len(all_programs),
            avg_roi=round(avg_roi, 1),
            top_category=top_cat,
            web3_count=web3_count,
            api_count=api_count,
        )

    def get_top_opportunities(self, n: int = 10) -> List[BountyProgram]:
        """Retorna los N programas con mejor ROI."""
        ranking = self.fetch_all(limit=50)
        return ranking.top_programs[:n]
