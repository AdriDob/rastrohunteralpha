import logging
from typing import Any

import requests

from core_engines.engine.unified_scoring import score_target as unified_score_target
from core_engines.targets import parser
from core_engines.targets.models import Scope, TargetIntel
from core_engines.targets.technology import (
    classify_cms,
    fingerprint_program,
    score_technology_relevance,
)
from database.db import SessionLocal, init_db

LOG = logging.getLogger("rastro.targets.hunter")


class Hunter:
    SUPPORTED_PLATFORMS = ["hackerone", "bugcrowd", "intigriti", "yeswehack"]

    def __init__(self):
        init_db()

    def fetch_public_programs(self, platform: str, limit: int = 50) -> list[dict]:
        """
        Attempt to fetch public program lists for a given platform.
        Tries multiple known endpoints and fallback approaches.
        If all fail, returns empty list (no crash).
        """
        platform = platform.lower()
        results: list[dict] = []
        urls: list[str] = []

        try:
            if platform == "hackerone":
                urls = [
                    "https://hackerone.com/bug-bounty-programs.json",
                    "https://hackerone.com/programs/search?query=&sort=popularity&page=1",
                ]
            elif platform == "bugcrowd":
                urls = [
                    "https://bugcrowd.com/programs.json",
                    "https://bugcrowd.com/programs?page=1",
                ]
            elif platform == "intigriti":
                urls = [
                    "https://api.intigriti.com/public/programs",
                    "https://app.intigriti.com/api/public/programs",
                ]
            elif platform == "yeswehack":
                urls = [
                    "https://yeswehack.com/api/programs",
                    "https://api.yeswehack.com/programs",
                ]
            else:
                return []

            data: Any = None
            last_error: str = ""
            for url in urls:
                try:
                    resp = requests.get(
                        url,
                        timeout=15,
                        headers={"User-Agent": "rastro/1.0 (+https://rastro.local)"},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        LOG.info("Fetched %d bytes from %s", len(resp.content), url)
                        break
                    last_error = f"status {resp.status_code}"
                except requests.RequestException as e:
                    last_error = str(e)
                    continue

            if data is None:
                LOG.debug("fetch_public_programs(%s) all endpoints failed: %s", platform, last_error)
                return []

            if isinstance(data, dict):
                for key in ("programs", "results", "data", "items", "rows"):
                    if key in data and isinstance(data[key], list):
                        programs = data[key]
                        break
                else:
                    programs = []
            elif isinstance(data, list):
                programs = data
            else:
                programs = []

            for p in programs[:limit]:
                name = p.get("name") or p.get("title") or p.get("handle") or p.get("program_name") or ""
                if not name:
                    continue
                scopes = p.get("scopes") or p.get("targets") or p.get("scope") or []
                results.append({
                    "name": name,
                    "scopes": scopes,
                    "domain": p.get("domain") or p.get("url") or p.get("website") or None,
                    "program_url": p.get("program_url") or p.get("url") or p.get("link") or None,
                    "source": platform,
                })
        except Exception as exc:
            LOG.debug("fetch_public_programs error for %s: %s", platform, exc)
        return results

    def ingest_programs(self, programs: list[dict]) -> list[dict]:
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

                # technology fingerprinting
                tech_tags = fingerprint_program(p)
                cms = classify_cms(tech_tags)
                wp_plugins = [t for t in tech_tags if t in (
                    "woocommerce", "elementor", "yoast", "acf",
                    "jetpack", "wpforms", "wordfence", "wprocket",
                )]
                tech_relevance = score_technology_relevance(tech_tags)

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
                    "technology_tags": tech_tags,
                    "technology_relevance": tech_relevance,
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
                    technology_tags=",".join(tech_tags),
                    cms_detected=cms or (tech_tags[0] if tech_tags else None),
                    framework_detected=next((t for t in tech_tags if t in (
                        "laravel", "django", "rails", "nextjs", "nuxt",
                        "spring", "fastapi", "flask", "express", "symfony",
                        "gatsby", "aspnet",
                    )), None),
                    wordpress_plugins_detected=",".join(wp_plugins) if wp_plugins else None,
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

    @staticmethod
    def list_programs(
        skip: int = 0,
        limit: int = 100,
        sort_by: str = "name",
        sort_order: str = "asc",
        search: str = "",
        technology: str = "",
    ) -> tuple:
        """Query persisted TargetIntel records as a discovery catalog.

        Returns (items, total_count).
        """
        session = SessionLocal()
        try:
            query = session.query(TargetIntel)

            if search:
                like = f"%{search}%"
                query = query.filter(
                    TargetIntel.name.ilike(like) | TargetIntel.domain.ilike(like)
                )

            if technology:
                like = f"%{technology.lower()}%"
                query = query.filter(
                    TargetIntel.technology_tags.ilike(like)
                )

            total = query.count()

            order_col = getattr(TargetIntel, sort_by, TargetIntel.name)
            order_fn = order_col.desc if sort_order == "desc" else order_col.asc
            query = query.order_by(order_fn())

            rows = query.offset(skip).limit(limit).all()

            items = []
            for r in rows:
                items.append({
                    "id": r.id,
                    "name": r.name,
                    "domain": r.domain,
                    "source": r.source,
                    "program_url": r.program_url,
                    "quality_score": r.quality_score,
                    "roi_score": r.roi_score,
                    "opportunity_score": r.opportunity_score,
                    "technology_tags": (r.technology_tags or "").split(",") if r.technology_tags else [],
                    "cms_detected": r.cms_detected,
                    "framework_detected": r.framework_detected,
                    "wordpress_plugins_detected": (r.wordpress_plugins_detected or "").split(",") if r.wordpress_plugins_detected else [],
                    "saas_probability": r.saas_probability,
                    "api_density": r.api_density,
                    "graphql_detected": r.graphql_detected,
                    "multi_tenant": r.multi_tenant,
                    "admin_detected": r.admin_detected,
                    "tags": r.tags,
                    "created_at": str(r.created_at) if r.created_at else None,
                })
            return items, total
        finally:
            session.close()

    @staticmethod
    def count_by_technology() -> list[dict]:
        """Return technology distribution across all programs."""
        session = SessionLocal()
        try:
            rows = session.query(TargetIntel).all()
            tech_count: dict[str, int] = {}
            for r in rows:
                if not r.technology_tags:
                    continue
                for tag in r.technology_tags.split(","):
                    tag = tag.strip()
                    if tag:
                        tech_count[tag] = tech_count.get(tag, 0) + 1
            sorted_tech = sorted(tech_count.items(), key=lambda x: -x[1])
            return [{"technology": k, "count": v} for k, v in sorted_tech]
        finally:
            session.close()
