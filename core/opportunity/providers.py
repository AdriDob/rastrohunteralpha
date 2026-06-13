"""Provider architecture for opportunity source aggregation.

Providers normalise public data into the Opportunity model.
All providers are read-only — never scan, exploit, or modify pipeline data.
Paid-first philosophy: programs with no rewards are marked accordingly.
"""

from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.opportunity.models import Opportunity, OpportunitySource, OpportunityProviderInfo

logger = logging.getLogger("rastro.opportunity.providers")

_GLOBAL_PROVIDERS: List[BaseProvider] = []


class BaseProvider(ABC):
    """Abstract base for all opportunity providers."""

    name: str = "base"
    category: str = "unknown"
    health_status: str = "healthy"

    def __init__(self) -> None:
        self._opportunities: List[Opportunity] = []
        self._last_refresh: Optional[str] = None

    @abstractmethod
    def discover(self) -> List[Opportunity]:
        """Fetch and return all available opportunities from this source."""
        ...

    @abstractmethod
    def refresh(self) -> List[Opportunity]:
        """Refresh opportunities, returning any new or updated items."""
        ...

    def normalize(self, raw: Dict[str, Any]) -> Optional[Opportunity]:
        """Convert raw data into an Opportunity model.

        Override in subclasses. Return None if data is invalid.
        """
        return None

    def info(self) -> OpportunityProviderInfo:
        return OpportunityProviderInfo(
            name=self.name,
            category=self.category,
            active=True,
            opportunity_count=len(self._opportunities),
            last_refresh=self._last_refresh,
            health_status=self.health_status,
        )

    def _make_id(self, raw: Dict[str, Any]) -> str:
        return f"{self.name}_{raw.get('id', str(uuid.uuid4())[:8])}"

    def _ts(self) -> str:
        return datetime.now(timezone.utc).isoformat()


class ManualProvider(BaseProvider):
    """Allows operators to manually define opportunities.

    Populated via the API. Data is stored in-memory (ephemeral).
    Session-backed persistence is handled by the database layer.
    """

    name = "manual"
    category = "independent"

    def discover(self) -> List[Opportunity]:
        return list(self._opportunities)

    def refresh(self) -> List[Opportunity]:
        return []

    def add(self, opp: Opportunity) -> None:
        self._opportunities.append(opp)


class PublicProgramProvider(BaseProvider):
    """Aggregates opportunities from public bug bounty program directories.

    Paid-first: VDP-only programs are marked with has_rewards=False.
    Supports categories: major_platforms, independent, web3, ai,
    open_source, infrastructure, api_ecosystems, cloud, mobile,
    browser_extensions, emerging, paid_research.
    """

    name = "public_programs"
    category = "platform"

    _SEED_OPPORTUNITIES: List[Dict[str, Any]] = [
        # ── Major Platforms ─────────────────────────────────────────────
        {
            "id": "hackerone_general",
            "name": "HackerOne Public Programs",
            "source_type": "platform", "source_name": "HackerOne",
            "source_url": "https://hackerone.com/bug-bounty-programs",
            "public_url": "https://hackerone.com/directory/programs",
            "scope_summary": "Thousands of public and private programs across all industries",
            "reward_info": "Varies by program — typically $500-$10,000+ per finding",
            "tech_tags": ["web", "api", "mobile", "cloud"],
            "confidence": 0.95, "has_rewards": True,
            "estimated_payout": 5000, "estimated_effort_hours": 3.0,
        },
        {
            "id": "bugcrowd_general",
            "name": "Bugcrowd Public Programs",
            "source_type": "platform", "source_name": "Bugcrowd",
            "source_url": "https://bugcrowd.com/programs",
            "public_url": "https://bugcrowd.com/programs",
            "scope_summary": "Diverse public and private programs with VRT-based scoring",
            "reward_info": "P30-P50+ per finding typical; varies by program",
            "tech_tags": ["web", "api", "mobile", "cloud", "hardware"],
            "confidence": 0.95, "has_rewards": True,
            "estimated_payout": 3000, "estimated_effort_hours": 3.0,
        },
        {
            "id": "intigriti_general",
            "name": "Intigriti Public Programs",
            "source_type": "platform", "source_name": "Intigriti",
            "source_url": "https://www.intigriti.com/programs",
            "public_url": "https://www.intigriti.com/programs",
            "scope_summary": "European-focused public and invite-only programs",
            "reward_info": "€500-€5,000+ per finding",
            "tech_tags": ["web", "api", "mobile"],
            "confidence": 0.9, "has_rewards": True,
            "estimated_payout": 2500, "estimated_effort_hours": 3.0,
        },
        {
            "id": "yeswehack_general",
            "name": "YesWeHack Public Programs",
            "source_type": "platform", "source_name": "YesWeHack",
            "source_url": "https://www.yeswehack.com/programs",
            "public_url": "https://www.yeswehack.com/programs",
            "scope_summary": "Global programs with responsible disclosure focus",
            "reward_info": "€500-€10,000 per finding",
            "tech_tags": ["web", "api", "mobile", "cloud"],
            "confidence": 0.85, "has_rewards": True,
            "estimated_payout": 3000, "estimated_effort_hours": 3.0,
        },
        # ── API Ecosystems ──────────────────────────────────────────────
        {
            "id": "api_ecosystems",
            "name": "API Security Programs",
            "source_type": "api_ecosystem", "source_name": "API Ecosystem",
            "source_url": "",
            "public_url": "",
            "scope_summary": "API-first companies running private/public bug bounty programs focused on REST, GraphQL, and gRPC endpoints",
            "reward_info": "$500-$15,000 per API vulnerability",
            "tech_tags": ["api", "graphql", "rest", "grpc", "oauth", "jwt"],
            "confidence": 0.7, "has_rewards": True,
            "estimated_payout": 4000, "estimated_effort_hours": 2.5,
        },
        # ── Cloud Infrastructure ────────────────────────────────────────
        {
            "id": "cloud_infrastructure",
            "name": "Cloud & Infrastructure Programs",
            "source_type": "infrastructure", "source_name": "Cloud",
            "source_url": "",
            "public_url": "",
            "scope_summary": "Cloud service providers and infrastructure companies with bug bounty programs covering IaaS, PaaS, and SaaS",
            "reward_info": "$1,000-$25,000 per finding depending on severity",
            "tech_tags": ["cloud", "aws", "gcp", "azure", "kubernetes", "docker", "infrastructure"],
            "confidence": 0.7, "has_rewards": True,
            "estimated_payout": 8000, "estimated_effort_hours": 4.0,
        },
        # ── Mobile Security ─────────────────────────────────────────────
        {
            "id": "mobile_security",
            "name": "Mobile Application Programs",
            "source_type": "mobile", "source_name": "Mobile",
            "source_url": "",
            "public_url": "",
            "scope_summary": "iOS and Android application security programs with native app testing scope",
            "reward_info": "$500-$10,000 per finding",
            "tech_tags": ["mobile", "ios", "android", "react-native", "flutter"],
            "confidence": 0.65, "has_rewards": True,
            "estimated_payout": 3000, "estimated_effort_hours": 3.5,
        },
        # ── Browser Extensions ──────────────────────────────────────────
        {
            "id": "browser_extensions",
            "name": "Browser Extension Security Programs",
            "source_type": "browser_extension", "source_name": "Browser Extensions",
            "source_url": "",
            "public_url": "",
            "scope_summary": "Security testing programs for browser extensions and plugins with millions of users",
            "reward_info": "$500-$5,000 per finding",
            "tech_tags": ["browser", "javascript", "typescript", "extension", "web"],
            "confidence": 0.6, "has_rewards": True,
            "estimated_payout": 2000, "estimated_effort_hours": 2.0,
        },
        # ── Open Source ─────────────────────────────────────────────────
        {
            "id": "open_source_bounties",
            "name": "Open Source Bug Bounties",
            "source_type": "open_source", "source_name": "Open Source",
            "source_url": "https://github.com",
            "public_url": "",
            "scope_summary": "Open source projects offering bounties for security vulnerabilities through platforms like GitHub Security Lab",
            "reward_info": "$500-$30,000 depending on project and severity",
            "tech_tags": ["web", "api", "open-source", "github"],
            "confidence": 0.7, "has_rewards": True,
            "estimated_payout": 5000, "estimated_effort_hours": 3.0,
        },
        # ── AI Security ──────────────────────────────────────────────────
        {
            "id": "ai_security",
            "name": "AI & LLM Security Programs",
            "source_type": "ai", "source_name": "AI Security",
            "source_url": "",
            "public_url": "",
            "scope_summary": "Emerging bug bounty programs for AI/ML models, LLM providers, and AI infrastructure",
            "reward_info": "$1,000-$50,000 for model vulnerabilities and data leakage",
            "tech_tags": ["ai", "ml", "llm", "python", "api", "cloud"],
            "confidence": 0.6, "has_rewards": True,
            "estimated_payout": 10000, "estimated_effort_hours": 4.0,
        },
        # ── Web3 ────────────────────────────────────────────────────────
        {
            "id": "web3_immunefi",
            "name": "Immunefi Web3 Programs",
            "source_type": "web3", "source_name": "Immunefi",
            "source_url": "https://immunefi.com/explore",
            "public_url": "https://immunefi.com/explore",
            "scope_summary": "Leading web3 bug bounty platform — DeFi, L1/L2, bridges, wallets",
            "reward_info": "Typically $50,000-$1,000,000+ for critical findings",
            "tech_tags": ["web3", "solidity", "rust", "move", "defi"],
            "confidence": 0.95, "has_rewards": True,
            "estimated_payout": 50000, "estimated_effort_hours": 5.0,
        },
        {
            "id": "web3_hackenproof",
            "name": "HackenProof Web3 Programs",
            "source_type": "web3", "source_name": "HackenProof",
            "source_url": "https://hackenproof.com/programs",
            "public_url": "https://hackenproof.com/programs",
            "scope_summary": "Web3 and crypto-focused bug bounty programs",
            "reward_info": "Up to $100,000+ per finding",
            "tech_tags": ["web3", "solidity", "defi"],
            "confidence": 0.85, "has_rewards": True,
            "estimated_payout": 20000, "estimated_effort_hours": 4.0,
        },
        {
            "id": "web3_code4rena",
            "name": "Code4rena Audit Contests",
            "source_type": "web3", "source_name": "Code4rena",
            "source_url": "https://code4rena.com/contests",
            "public_url": "https://code4rena.com/contests",
            "scope_summary": "Competitive smart contract audit contests with prize pools",
            "reward_info": "Prize pools typically $20,000-$100,000+",
            "tech_tags": ["web3", "solidity"],
            "confidence": 0.9, "has_rewards": True,
            "estimated_payout": 15000, "estimated_effort_hours": 3.0,
        },
        {
            "id": "web3_hats",
            "name": "Hats Finance Vaults",
            "source_type": "web3", "source_name": "Hats Finance",
            "source_url": "https://hats.finance/vaults",
            "public_url": "https://hats.finance/vaults",
            "scope_summary": "Continuous web3 security vaults with peer review",
            "reward_info": "Vault-based rewards, varies by protocol",
            "tech_tags": ["web3", "solidity"],
            "confidence": 0.8, "has_rewards": True,
            "estimated_payout": 10000, "estimated_effort_hours": 3.0,
        },
        # ── Independent Programs ────────────────────────────────────────
        {
            "id": "independent_public_bug_bounties",
            "name": "Independent & Self-Run Programs",
            "source_type": "independent", "source_name": "Independent",
            "source_url": "",
            "public_url": "",
            "scope_summary": "Companies running their own bug bounty programs outside major platforms",
            "reward_info": "Varies widely — some offer swag, some offer cash",
            "tech_tags": ["web", "api", "mobile", "cloud", "hardware"],
            "confidence": 0.7, "has_rewards": True,
            "estimated_payout": 1500, "estimated_effort_hours": 2.0,
        },
        # ── disclose.io (VDP — no rewards) ──────────────────────────────
        {
            "id": "disclose_io",
            "name": "disclose.io / VDP Directory",
            "source_type": "platform", "source_name": "disclose.io",
            "source_url": "https://disclose.io",
            "public_url": "https://disclose.io",
            "scope_summary": "Curated directory of responsible disclosure programs",
            "reward_info": "Mostly VDP (no financial reward); some offer bounties",
            "tech_tags": ["web", "api"],
            "confidence": 0.9, "has_rewards": False,
            "estimated_payout": 0, "estimated_effort_hours": 1.0,
        },
        # ── Paid Research ───────────────────────────────────────────────
        {
            "id": "paid_research_programs",
            "name": "Paid Research Opportunities",
            "source_type": "paid_research", "source_name": "Paid Research",
            "source_url": "",
            "public_url": "",
            "scope_summary": "Direct paid research engagements and retainer-based security testing programs",
            "reward_info": "$5,000-$100,000+ per engagement",
            "tech_tags": ["web", "api", "cloud", "mobile", "infrastructure"],
            "confidence": 0.65, "has_rewards": True,
            "estimated_payout": 20000, "estimated_effort_hours": 20.0,
        },
        # ── Emerging Programs ───────────────────────────────────────────
        {
            "id": "emerging_critical_startups",
            "name": "High-Growth Startup Programs",
            "source_type": "emerging", "source_name": "Emerging",
            "source_url": "",
            "public_url": "",
            "scope_summary": "Newly launched bug bounty programs from high-growth startups",
            "reward_info": "Often higher rewards due to lower competition",
            "tech_tags": ["web", "api", "mobile", "cloud"],
            "confidence": 0.6, "has_rewards": True,
            "estimated_payout": 3000, "estimated_effort_hours": 2.0,
        },
        {
            "id": "emerging_vdp_launches",
            "name": "New VDP / Disclosure Page Launches",
            "source_type": "emerging", "source_name": "Emerging",
            "source_url": "",
            "public_url": "",
            "scope_summary": "Recently published vulnerability disclosure programs",
            "reward_info": "Mostly VDP; some offer swag or bounties",
            "tech_tags": ["web", "api"],
            "confidence": 0.5, "has_rewards": False,
            "estimated_payout": 0, "estimated_effort_hours": 1.0,
        },
        # ── Research ────────────────────────────────────────────────────
        {
            "id": "research_academic",
            "name": "Academic & Research Programs",
            "source_type": "research", "source_name": "Research",
            "source_url": "",
            "public_url": "",
            "scope_summary": "University and research institution disclosure programs",
            "reward_info": "Typically recognition-based",
            "tech_tags": ["web", "api", "research"],
            "confidence": 0.5, "has_rewards": False,
            "estimated_payout": 0, "estimated_effort_hours": 2.0,
        },
    ]

    def discover(self) -> List[Opportunity]:
        now = datetime.now(timezone.utc).isoformat()
        self._opportunities = []
        for seed in self._SEED_OPPORTUNITIES:
            opp = Opportunity(
                id=self._make_id(seed),
                name=seed["name"],
                source=OpportunitySource(
                    type=seed["source_type"],
                    name=seed["source_name"],
                    url=seed.get("source_url", ""),
                    confidence=seed["confidence"],
                ),
                category=seed["source_type"],
                public_url=seed.get("public_url", ""),
                scope_summary=seed["scope_summary"],
                reward_info=seed.get("reward_info", ""),
                technology_tags=seed.get("tech_tags", []),
                confidence=seed["confidence"],
                created_at=now,
                has_rewards=seed.get("has_rewards", True),
                estimated_payout=seed.get("estimated_payout", 0.0),
                estimated_effort_hours=seed.get("estimated_effort_hours", 2.0),
            )
            self._opportunities.append(opp)
        self._last_refresh = now
        logger.info("Discovered %d public opportunities (paid-first: %d with rewards)",
                     len(self._opportunities),
                     sum(1 for o in self._opportunities if o.has_rewards))
        return list(self._opportunities)

    def refresh(self) -> List[Opportunity]:
        self._last_refresh = datetime.now(timezone.utc).isoformat()
        return []


class GitHubAdvisoryProvider(BaseProvider):
    """GitHub Security Bug Bounty / GitHub Advisory Database.

    Covers open-source vulnerability reporting with reward potential.
    """

    name = "github_security"
    category = "open_source"

    _SEEDS: List[Dict[str, Any]] = [
        {
            "id": "github_security_lab",
            "name": "GitHub Security Lab Bounty",
            "source_type": "open_source", "source_name": "GitHub Security Lab",
            "source_url": "https://securitylab.github.com",
            "public_url": "https://bounty.github.com",
            "scope_summary": "Vulnerabilities in high-impact open source projects on GitHub",
            "reward_info": "$10,000-$30,000+ per vulnerability in eligible projects",
            "tech_tags": ["web", "api", "open-source", "github"],
            "confidence": 0.9, "has_rewards": True,
            "estimated_payout": 15000, "estimated_effort_hours": 5.0,
        },
        {
            "id": "github_advisories",
            "name": "GitHub Advisory Database Contributions",
            "source_type": "open_source", "source_name": "GitHub Advisory Database",
            "source_url": "https://github.com/advisories",
            "public_url": "https://github.com/advisories",
            "scope_summary": "Contributing security advisories to GitHub's global advisory database",
            "reward_info": "Recognition and CVE assignment; some projects offer bounties",
            "tech_tags": ["web", "open-source"],
            "confidence": 0.7, "has_rewards": False,
            "estimated_payout": 0, "estimated_effort_hours": 2.0,
        },
    ]

    def discover(self) -> List[Opportunity]:
        now = datetime.now(timezone.utc).isoformat()
        self._opportunities = []
        for seed in self._SEEDS:
            opp = Opportunity(
                id=self._make_id(seed),
                name=seed["name"],
                source=OpportunitySource(
                    type=seed["source_type"],
                    name=seed["source_name"],
                    url=seed.get("source_url", ""),
                    confidence=seed["confidence"],
                ),
                category=seed["source_type"],
                public_url=seed.get("public_url", ""),
                scope_summary=seed["scope_summary"],
                reward_info=seed.get("reward_info", ""),
                technology_tags=seed.get("tech_tags", []),
                confidence=seed["confidence"],
                created_at=now,
                has_rewards=seed.get("has_rewards", True),
                estimated_payout=seed.get("estimated_payout", 0.0),
                estimated_effort_hours=seed.get("estimated_effort_hours", 2.0),
            )
            self._opportunities.append(opp)
        self._last_refresh = now
        return list(self._opportunities)

    def refresh(self) -> List[Opportunity]:
        self._last_refresh = datetime.now(timezone.utc).isoformat()
        return []


class HuntrProvider(BaseProvider):
    """Huntr (by ProtectAI) — open-source vulnerability disclosure platform.

    First-class provider for finding vulnerabilities in open-source projects
    with reward potential.
    """

    name = "huntr"
    category = "open_source"

    _SEEDS: List[Dict[str, Any]] = [
        {
            "id": "huntr_main",
            "name": "huntr — Open Source Bug Bounty",
            "source_type": "open_source", "source_name": "huntr",
            "source_url": "https://huntr.com",
            "public_url": "https://huntr.com/bounties",
            "scope_summary": "Open source vulnerability disclosure and bug bounty platform by ProtectAI",
            "reward_info": "$100-$10,000+ per vulnerability depending on severity and project impact",
            "tech_tags": ["web", "api", "open-source", "python", "javascript"],
            "confidence": 0.9, "has_rewards": True,
            "estimated_payout": 2500, "estimated_effort_hours": 2.0,
        },
        {
            "id": "huntr_ml_projects",
            "name": "huntr ML/AI Security Bounties",
            "source_type": "ai", "source_name": "huntr",
            "source_url": "https://huntr.com/bounties",
            "public_url": "https://huntr.com/bounties",
            "scope_summary": "ML/AI open source project vulnerability bounties on huntr platform",
            "reward_info": "$500-$5,000 per ML/AI vulnerability",
            "tech_tags": ["ai", "ml", "python", "open-source"],
            "confidence": 0.85, "has_rewards": True,
            "estimated_payout": 2000, "estimated_effort_hours": 3.0,
        },
    ]

    def discover(self) -> List[Opportunity]:
        now = datetime.now(timezone.utc).isoformat()
        self._opportunities = []
        for seed in self._SEEDS:
            opp = Opportunity(
                id=self._make_id(seed),
                name=seed["name"],
                source=OpportunitySource(
                    type=seed["source_type"],
                    name=seed["source_name"],
                    url=seed.get("source_url", ""),
                    confidence=seed["confidence"],
                ),
                category=seed["source_type"],
                public_url=seed.get("public_url", ""),
                scope_summary=seed["scope_summary"],
                reward_info=seed.get("reward_info", ""),
                technology_tags=seed.get("tech_tags", []),
                confidence=seed["confidence"],
                created_at=now,
                has_rewards=seed.get("has_rewards", True),
                estimated_payout=seed.get("estimated_payout", 0.0),
                estimated_effort_hours=seed.get("estimated_effort_hours", 2.0),
            )
            self._opportunities.append(opp)
        self._last_refresh = now
        return list(self._opportunities)

    def refresh(self) -> List[Opportunity]:
        self._last_refresh = datetime.now(timezone.utc).isoformat()
        return []


class AllSourcesProvider(BaseProvider):
    """Aggregates all known opportunity sources into a single provider.

    This provides a comprehensive view spanning all categories.
    """

    name = "all_sources"
    category = "platform"

    def discover(self) -> List[Opportunity]:
        now = datetime.now(timezone.utc).isoformat()
        all_seeds = PublicProgramProvider._SEED_OPPORTUNITIES + GitHubAdvisoryProvider._SEEDS + HuntrProvider._SEEDS
        self._opportunities = []
        for seed in all_seeds:
            opp = Opportunity(
                id=f"all_{seed['id']}",
                name=seed["name"],
                source=OpportunitySource(
                    type=seed["source_type"],
                    name=seed["source_name"],
                    url=seed.get("source_url", ""),
                    confidence=seed["confidence"],
                ),
                category=seed["source_type"],
                public_url=seed.get("public_url", ""),
                scope_summary=seed["scope_summary"],
                reward_info=seed.get("reward_info", ""),
                technology_tags=seed.get("tech_tags", []),
                confidence=seed["confidence"],
                created_at=now,
                has_rewards=seed.get("has_rewards", True),
                estimated_payout=seed.get("estimated_payout", 0.0),
                estimated_effort_hours=seed.get("estimated_effort_hours", 2.0),
            )
            self._opportunities.append(opp)
        self._last_refresh = now
        return list(self._opportunities)

    def refresh(self) -> List[Opportunity]:
        self._last_refresh = datetime.now(timezone.utc).isoformat()
        return []


def register_provider(provider: BaseProvider) -> None:
    """Register a provider singleton."""
    _GLOBAL_PROVIDERS.append(provider)


def get_providers() -> List[BaseProvider]:
    """Return all registered provider instances."""
    if not _GLOBAL_PROVIDERS:
        register_provider(ManualProvider())
        register_provider(PublicProgramProvider())
        register_provider(GitHubAdvisoryProvider())
        register_provider(HuntrProvider())
        register_provider(AllSourcesProvider())
    return list(_GLOBAL_PROVIDERS)


def get_provider(name: str) -> Optional[BaseProvider]:
    for p in get_providers():
        if p.name == name:
            return p
    return None
