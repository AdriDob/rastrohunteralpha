import logging
from typing import List, Dict, Optional

import requests

from database.db import SessionLocal, init_db
from core.targets import parser, filters
from core.engine.unified_scoring import score_target as unified_score_target
from core.targets.models import TargetIntel, Scope

LOG = logging.getLogger("rastro.targets.hunter")


class Hunter:
    SUPPORTED_PLATFORMS = ["hackerone", "bugcrowd", "intigriti", "yeswehack"]

    def __init__(self):
        init_db()

    def fetch_public_programs(self, platform: str, limit: int = 50) -> List[Dict]:
        """
        Attempt to fetch public program lists for a given platform. This method is conservative:
        - Tries known public JSON endpoints when available
        - If response is non-JSON or errors, returns empty list
        """
        platform = platform.lower()
        results = []
        try:
            if platform == "hackerone":
                url = "https://hackerone.com/bug-bounty-programs.json"
            elif platform == "bugcrowd":
                url = "https://bugcrowd.com/programs.json"
            elif platform == "intigriti":
                url = "https://api.intigriti.com/public/programs"  # may require pagination
            elif platform == "yeswehack":
                url = "https://yeswehack.com/api/programs"
            else:
                return []

            resp = requests.get(
                url,
                timeout=10,
                headers={"User-Agent": "rastro/1.0 (+https://rastro.local)"},
            )
            if resp.status_code != 200:
                LOG.debug("No public listing at %s (status %s)", url, resp.status_code)
                return []
            data = resp.json()
            # Expect data to be a list or contain 'programs'
            if isinstance(data, dict) and "programs" in data:
                programs = data["programs"]
            elif isinstance(data, list):
                programs = data
            else:
                programs = []

            for p in programs[:limit]:
                # normalize minimal fields
                results.append(
                    {
                        "name": p.get("name") or p.get("title") or p.get("handle"),
                        "scopes": p.get("scopes") or p.get("targets") or [],
                        "domain": p.get("domain") or p.get("url") or None,
                        "program_url": p.get("url") or p.get("program_url") or None,
                        "source": platform,
                    }
                )
        except Exception as exc:
            LOG.debug("fetch_public_programs error for %s: %s", platform, exc)
        return results

    def ingest_programs(self, programs: List[Dict]) -> List[Dict]:
        """Parse provided program dicts, score them and persist to DB."""
        saved = []
        session = SessionLocal()
        try:
            for p in programs:
                name = p.get("name") or p.get("title") or "unnamed"
                source = p.get("source") or "imported"
                
                # Idempotent deduplication check
                exists = session.query(TargetIntel).filter(
                    TargetIntel.name == name,
                    TargetIntel.source == source
                ).first()
                if exists:
                    continue

                scopes = p.get("scopes") or p.get("scope") or []
                domain = p.get("domain") or p.get("program_url")

                # parse scopes
                parsed = parser.parse_program_scopes(scopes)

                # basic metadata aggregation
                api_count = sum(1 for s in parsed if s.get("is_api"))
                graphql = any(s.get("is_graphql") for s in parsed)
                wildcard = any(s.get("is_wildcard") for s in parsed)

                # heuristics for SaaS/B2B/admin/multi-tenant
                keywords = " ".join(scopes).lower()
                saas_prob = (
                    0.8 if any(k in keywords for k in ["saas", "app.", "app-"]) else 0.2
                )
                b2b = any(
                    k in keywords for k in ["enterprise", "b2b", "business", "company"]
                )
                admin = any(k in keywords for k in ["admin", "dashboard", "panel"])
                multi_tenant = (
                    any(
                        k in keywords
                        for k in [
                            "org_id",
                            "tenant",
                            "workspace",
                            "account_id",
                            "team_id",
                        ]
                    )
                    or wildcard
                )
                export = "export" in keywords or "download" in keywords
                auth_heavy = any(
                    k in keywords for k in ["login", "signup", "auth", "session"]
                )
                static = any(
                    k in keywords for k in ["blog", "wordpress", "marketing", "landing"]
                )

                meta = {
                    "graphql": graphql,
                    "api_count": api_count,
                    "saas_prob": saas_prob,
                    "b2b": b2b,
                    "admin": admin,
                    "export": export,
                    "multi_tenant": multi_tenant,
                    "auth_heavy": auth_heavy,
                    "static": static,
                    "source": source,
                    "wildcard": wildcard,
                }

                scores = unified_score_target(meta)

                intel = TargetIntel(
                    name=name,
                    domain=domain,
                    source=source,
                    program_url=p.get("program_url") or p.get("program") or None,
                    quality_score=scores["quality"],
                    complexity_score=scores["complexity_score"],
                    roi_score=scores["roi_score"],
                    noise_score=0,
                    freshness_score=scores.get("freshness_score", 0.0),
                    competition_score=scores.get("competition_score", 0.0),
                    opportunity_score=scores.get("opportunity_score", 0.0),
                    reward_score=50.0,
                    reward_confidence=0.0,
                    attack_surface_score=scores.get("attack_surface_score", 0.0),
                    evidence_potential_score=0.0,
                    saas_probability=saas_prob,
                    api_density=api_count,
                    graphql_detected=graphql,
                    b2b_indicator=b2b,
                    admin_detected=admin,
                    multi_tenant=multi_tenant,
                    tags=",".join(
                        sorted({"bookmarked"} if p.get("bookmarked") else set())
                    ),
                )

                session.add(intel)
                session.flush()  # get id

                # store scopes
                for s in parsed:
                    for d in s.get("domains", []) or [None]:
                        sc = Scope(
                            target_id=intel.id,
                            scope_text=s.get("scope_text"),
                            is_wildcard=bool(s.get("is_wildcard")),
                            is_api=bool(s.get("is_api")),
                            is_graphql=bool(s.get("is_graphql")),
                            extracted_domain=d,
                        )
                        session.add(sc)

                session.commit()
                saved.append(
                    {"id": intel.id, "name": name, "domain": domain, "scores": scores}
                )
        finally:
            session.close()
        return saved
