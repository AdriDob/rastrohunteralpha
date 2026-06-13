"""
Rastro Investigation Narrator — interprets existing system state.

Provides human-readable explanations of investigation state, attack paths,
report narratives, unified Web2+Web3 analysis, and bounty potential.

ALL data is derived from real system state. No vulnerability detection.
No scan execution. No data modification. Pure interpretation layer.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from database import db, models
from core.engine.unified_scoring import score as unified_score, score_target as unified_score_target
from core.evidence.graph import EvidenceGraph
from core.evidence.store import EvidenceStore
from core.reporting.report_engine import ReportEngine, FinalReport, ProgramData
from core.reporting.severity import risk_to_severity, severity_score, confidence_to_label
from core.validation.gate import Verdict
from core.validation.rules import ValidationReport, RuleResult
from core.validation.confidence import ConfidenceScore
from core.opportunity.engine import get_engine as get_opportunity_engine

logger = logging.getLogger("rastro.assistant.narrator")


class InvestigationNarrator:
    """Interprets real system data into human-readable investigation intelligence."""

    @staticmethod
    def _parse_conf(val: object) -> float:
        if val is None:
            return 0.0
        try:
            if isinstance(val, str):
                val = val.strip()
                if val.startswith("{"):
                    parsed = json.loads(val)
                    return float(parsed.get("score", parsed.get("confidence", 0)))
            return float(val)
        except (ValueError, TypeError, json.JSONDecodeError):
            return 0.0

    @staticmethod
    def _parse_json_field(val: object, default: dict) -> dict:
        if isinstance(val, dict):
            return val
        if isinstance(val, str):
            try:
                parsed = json.loads(val)
                return parsed if isinstance(parsed, dict) else default
            except (json.JSONDecodeError, TypeError):
                return default
        return default

    def explain_investigation_state(self, target_id: int) -> Dict[str, Any]:
        """Interpret the current investigation state for a target.

        Combines graph topology, evidence, verdicts, and findings into
        a coherent explanation of what is known and what needs attention.
        """
        session = db.SessionLocal()
        try:
            target = session.query(models.Target).filter(models.Target.id == target_id).first()
            if not target:
                return {"error": "Target not found", "target_id": target_id}

            endpoints = session.query(models.Endpoint).filter(models.Endpoint.target_id == target_id).all()
            findings = session.query(models.Finding).filter(models.Finding.target_id == target_id).all()
            verdicts = session.query(models.Verdict).filter(
                models.Verdict.endpoint_id.in_([ep.id for ep in endpoints])
            ).all() if endpoints else []

            scored_endpoints = []
            for ep in endpoints:
                s = unified_score(ep.path, ep.method or "GET", ep.parsed_params)
                scored_endpoints.append({
                    "id": ep.id,
                    "path": ep.path,
                    "method": ep.method,
                    "risk_score": s.get("risk_score", 0),
                    "vector": s.get("vector", ""),
                    "signals": s.get("signals", []),
                    "labels": s.get("labels", []),
                    "attack_surface": s.get("attack_surface", []),
                    "actionable": s.get("actionable", False),
                    "target_id": ep.target_id,
                })

            confirmed_verdicts = [v for v in verdicts if v.status == "confirmed"]
            rejected_verdicts = [v for v in verdicts if v.status == "rejected"]
            inconclusive_verdicts = [v for v in verdicts if v.status == "inconclusive"]

            high_risk_eps = [ep for ep in endpoints if any(
                v.endpoint_id == ep.id for v in confirmed_verdicts
            )]

            findings_by_severity: Dict[str, int] = {}
            for f in findings:
                sev = f.severity or "info"
                findings_by_severity[sev] = findings_by_severity.get(sev, 0) + 1

            return {
                "target": {"id": target.id, "name": target.name, "domain": target.domain},
                "coverage": {
                    "total_endpoints": len(endpoints),
                    "scored": len(scored_endpoints),
                    "actionable": sum(1 for e in scored_endpoints if e["actionable"]),
                    "high_risk": len(high_risk_eps),
                    "total_findings": len(findings),
                },
                "verdicts": {
                    "total": len(verdicts),
                    "confirmed": len(confirmed_verdicts),
                    "rejected": len(rejected_verdicts),
                    "inconclusive": len(inconclusive_verdicts),
                    "confidence_avg": (
                        sum(self._parse_conf(v.confidence) for v in confirmed_verdicts) / len(confirmed_verdicts)
                        if confirmed_verdicts else 0
                    ),
                },
                "findings_by_severity": findings_by_severity,
                "interpretation": self._interpret_state(
                    target=target,
                    scored_endpoints=scored_endpoints,
                    verdicts=verdicts,
                    findings=findings,
                ),
            }
        finally:
            session.close()

    def generate_report_narrative(self, target_id: int) -> Dict[str, Any]:
        """Generate a HackerOne/Immunefi-style report narrative from real findings.

        Uses existing confirmed verdicts and evidence to produce
        a submission-ready narrative. Does NOT detect vulnerabilities.
        """
        session = db.SessionLocal()
        try:
            target = session.query(models.Target).filter(models.Target.id == target_id).first()
            if not target:
                return {"error": "Target not found", "target_id": target_id}

            endpoints = session.query(models.Endpoint).filter(models.Endpoint.target_id == target_id).all()
            verdicts = session.query(models.Verdict).filter(
                models.Verdict.endpoint_id.in_([ep.id for ep in endpoints])
            ).all() if endpoints else []

            confirmed_verdicts = [v for v in verdicts if v.status == "confirmed"]
            if not confirmed_verdicts:
                return {
                    "target": {"id": target.id, "name": target.name},
                    "narratives": [],
                    "message": "No confirmed findings to report. Run validation first.",
                }

            ep_map = {ep.id: ep for ep in endpoints}
            evidence_store = EvidenceStore()
            report_engine = ReportEngine(evidence_store)
            program = ProgramData(
                name=target.name or "Private Program",
                platform="hackerone",
                bounty_range=self._estimate_bounty_range(confirmed_verdicts),
            )

            narratives = []
            for verdict in confirmed_verdicts[:10]:
                ep = ep_map.get(verdict.endpoint_id) if verdict.endpoint_id else None
                ep_data = {
                    "path": ep.path if ep else "/unknown",
                    "method": ep.method or "GET",
                    "risk_score": unified_score(ep.path, ep.method or "GET", ep.parsed_params).get("risk_score", 50)
                    if ep else 50,
                }
                evidence_list = evidence_store.get_evidence_for_verdict(verdict.id)

                validation_data = self._parse_json_field(verdict.validation_report, {})
                passed_rules = validation_data.get("passed_rules", []) if isinstance(validation_data, dict) else []
                failed_rules = validation_data.get("failed_rules", []) if isinstance(validation_data, dict) else []

                conf_details_raw = self._parse_json_field(verdict.confidence_details, {})
                conf_score_val = float(conf_details_raw.get("score", self._parse_conf(verdict.confidence))) if isinstance(conf_details_raw, dict) else self._parse_conf(verdict.confidence)
                conf_level = conf_details_raw.get("level", "medium") if isinstance(conf_details_raw, dict) else "medium"
                conf_breakdown = conf_details_raw.get("breakdown", {}) if isinstance(conf_details_raw, dict) else {}

                v = Verdict(
                    hot_path_id=verdict.hot_path_id or f"v{verdict.id}",
                    status=verdict.status,
                    confidence=conf_score_val,
                    reproducibility_score=float(verdict.reproducibility_score) if verdict.reproducibility_score else 0,
                    validation=ValidationReport(
                        passed=len(passed_rules) > 0,
                        passed_rules=passed_rules,
                        failed_rules=failed_rules,
                        details={},
                    ),
                    confidence_details=ConfidenceScore(
                        score=conf_score_val,
                        breakdown=conf_breakdown,
                        level=conf_level,
                    ),
                    evidence_links=verdict.evidence_links or [],
                    reason=verdict.reason or "",
                    retry_count=int(verdict.retry_count) if verdict.retry_count else 0,
                    timestamp=verdict.created_at.isoformat() if verdict.created_at else "",
                )

                report = report_engine.build(v, program, ep_data, evidence_list)
                if report:
                    narratives.append(self._format_narrative_output(report, target.name or ""))
                else:
                    narratives.append({
                        "hot_path_id": verdict.hot_path_id or f"v{verdict.id}",
                        "status": "no_report",
                        "reason": "Below confidence threshold for report generation",
                    })

            return {
                "target": {"id": target.id, "name": target.name, "domain": target.domain},
                "program": {"name": program.name, "platform": program.platform, "bounty_range": program.bounty_range},
                "narratives": narratives,
                "total_confirmed": len(confirmed_verdicts),
                "narratives_generated": sum(1 for n in narratives if n.get("status") != "no_report"),
            }
        finally:
            session.close()

    def explain_attack_path(self, hot_path_id: str) -> Dict[str, Any]:
        """Explain why a specific hot path exists and what it means.

        Analyzes the hot path's cluster composition, endpoint risk scores,
        and entity relationships to produce a human-readable explanation.
        """
        session = db.SessionLocal()
        try:
            parts = hot_path_id.split(":")
            if len(parts) < 2:
                return {"error": "Invalid hot_path_id format", "hot_path_id": hot_path_id}

            path_type = parts[0]
            path_value = ":".join(parts[1:])

            verdicts = session.query(models.Verdict).filter(
                models.Verdict.hot_path_id.like(f"%{path_value}%")
            ).all() if path_value else []
            endpoints = session.query(models.Endpoint).all()
            findings = session.query(models.Finding).all()

            scored_endpoints = []
            for ep in endpoints:
                s = unified_score(ep.path, ep.method or "GET", ep.parsed_params)
                scored_endpoints.append({
                    "id": ep.id,
                    "path": ep.path,
                    "method": ep.method,
                    "risk_score": s.get("risk_score", 0),
                    "vector": s.get("vector", ""),
                    "signals": s.get("signals", []),
                    "labels": s.get("labels", []),
                    "attack_surface": s.get("attack_surface", []),
                    "target_id": ep.target_id,
                })

            high_risk = [e for e in scored_endpoints if e["risk_score"] >= 50]
            actionable = [e for e in scored_endpoints if e.get("actionable")]

            target_ids = set()
            for e in scored_endpoints:
                target_ids.add(e.get("target_id") or 0)
            targets = session.query(models.Target).filter(models.Target.id.in_(list(target_ids))).all() if target_ids else []
            target_map = {t.id: t.name for t in targets}

            confirmed_verdicts = [v for v in verdicts if v.status == "confirmed"]
            surfaces: Dict[str, int] = {}
            for e in scored_endpoints:
                for s in e.get("attack_surface", []):
                    surfaces[s] = surfaces.get(s, 0) + 1

            return {
                "hot_path_id": hot_path_id,
                "path_type": path_type,
                "description": self._describe_path_type(path_type),
                "path_value": path_value,
                "risk_context": {
                    "high_risk_endpoints": len(high_risk),
                    "actionable_endpoints": len(actionable),
                    "total_relevant_endpoints": len(scored_endpoints),
                    "confirmed_verdicts_on_path": len(confirmed_verdicts),
                },
                "involved_targets": [
                    {"id": tid, "name": target_map.get(tid, f"target_{tid}")}
                    for tid in sorted(target_ids) if tid > 0
                ],
                "attack_surfaces": [
                    {"surface": k, "count": v}
                    for k, v in sorted(surfaces.items(), key=lambda x: -x[1])
                ],
                "explanation": self._generate_path_explanation(
                    path_type=path_type,
                    path_value=path_value,
                    high_risk_count=len(high_risk),
                    confirmed_count=len(confirmed_verdicts),
                    surfaces=surfaces,
                ),
                "recommended_action": self._recommend_path_action(
                    confirmed_count=len(confirmed_verdicts),
                    high_risk_count=len(high_risk),
                    actionable_count=len(actionable),
                ),
            }
        finally:
            session.close()

    def unified_reasoning(self, target_id: int) -> Dict[str, Any]:
        """Merge Web2 (endpoints) and Web3 (contracts) analysis into a single narrative.

        Shows how web3 surfaces connect to traditional API endpoints
        and what the combined attack surface looks like.
        """
        session = db.SessionLocal()
        try:
            target = session.query(models.Target).filter(models.Target.id == target_id).first()
            if not target:
                return {"error": "Target not found", "target_id": target_id}

            endpoints = session.query(models.Endpoint).filter(models.Endpoint.target_id == target_id).all()
            findings = session.query(models.Finding).filter(models.Finding.target_id == target_id).all()
            verdicts = session.query(models.Verdict).filter(
                models.Verdict.endpoint_id.in_([ep.id for ep in endpoints])
            ).all() if endpoints else []

            web2_endpoints = []
            web3_endpoints = []

            for ep in endpoints:
                s = unified_score(ep.path, ep.method or "GET", ep.parsed_params)
                signals = s.get("signals", [])
                labels = s.get("labels", [])
                is_web3 = "web3" in signals or "web3" in labels or any(
                    kw in (ep.path or "").lower()
                    for kw in ["wallet", "balance", "transfer", "tx", "transaction",
                               "signature", "nonce", "rpc", "infura", "alchemy",
                               "contract", "ethereum", "solana", "chain", "eth_", "jsonrpc"]
                )
                ep_data = {
                    "id": ep.id,
                    "path": ep.path,
                    "method": ep.method,
                    "risk_score": s.get("risk_score", 0),
                    "vector": s.get("vector", ""),
                    "signals": signals,
                    "labels": labels,
                    "surfaces": s.get("attack_surface", []),
                    "actionable": s.get("actionable", False),
                }
                if is_web3:
                    web3_endpoints.append(ep_data)
                else:
                    web2_endpoints.append(ep_data)

            web3_findings = [f for f in findings if f.endpoint_id and any(
                we["id"] == f.endpoint_id for we in web3_endpoints
            )]
            web3_verdicts = [v for v in verdicts if v.endpoint_id and any(
                we["id"] == v.endpoint_id for we in web3_endpoints
            )]

            return {
                "target": {"id": target.id, "name": target.name, "domain": target.domain},
                "web2_analysis": {
                    "endpoint_count": len(web2_endpoints),
                    "high_risk": sum(1 for e in web2_endpoints if e["risk_score"] >= 50),
                    "actionable": sum(1 for e in web2_endpoints if e["actionable"]),
                    "top_vectors": self._top_vectors(web2_endpoints),
                    "top_signals": self._top_signals(web2_endpoints),
                },
                "web3_analysis": {
                    "endpoint_count": len(web3_endpoints),
                    "high_risk": sum(1 for e in web3_endpoints if e["risk_score"] >= 50),
                    "actionable": sum(1 for e in web3_endpoints if e["actionable"]),
                    "findings": len(web3_findings),
                    "verdicts": len(web3_verdicts),
                    "top_vectors": self._top_vectors(web3_endpoints),
                    "top_signals": self._top_signals(web3_endpoints),
                },
                "unified_narrative": self._generate_unified_narrative(
                    target_name=target.name or "",
                    web2_count=len(web2_endpoints),
                    web3_count=len(web3_endpoints),
                    web2_high_risk=sum(1 for e in web2_endpoints if e["risk_score"] >= 50),
                    web3_high_risk=sum(1 for e in web3_endpoints if e["risk_score"] >= 50),
                    web3_findings=len(web3_findings),
                    web3_verdicts=len(web3_verdicts),
                ),
                "attack_surface_merge": self._merge_surfaces(web2_endpoints, web3_endpoints),
            }
        finally:
            session.close()

    def explain_bounty_potential(self, target_id: int) -> Dict[str, Any]:
        """Explain potential bounty payout based on real system signals.

        Uses opportunity scoring, confirmed findings, endpoint complexity,
        and market data to estimate payout potential.
        """
        session = db.SessionLocal()
        try:
            target = session.query(models.Target).filter(models.Target.id == target_id).first()
            if not target:
                return {"error": "Target not found", "target_id": target_id}

            endpoints = session.query(models.Endpoint).filter(models.Endpoint.target_id == target_id).all()
            findings = session.query(models.Finding).filter(models.Finding.target_id == target_id).all()
            verdicts = session.query(models.Verdict).filter(
                models.Verdict.endpoint_id.in_([ep.id for ep in endpoints])
            ).all() if endpoints else []

            scored_endpoints = []
            for ep in endpoints:
                s = unified_score(ep.path, ep.method or "GET", ep.parsed_params)
                scored_endpoints.append({
                    "id": ep.id,
                    "path": ep.path,
                    "method": ep.method,
                    "risk_score": s.get("risk_score", 0),
                    "vector": s.get("vector", ""),
                    "signals": s.get("signals", []),
                    "labels": s.get("labels", []),
                    "attack_surface": s.get("attack_surface", []),
                    "actionable": s.get("actionable", False),
                    "potential_idor": s.get("potential_idor", False),
                })

            roi = unified_score_target({
                "api_count": len(endpoints),
                "has_graphql": any("/graphql" in (ep.path or "").lower() for ep in endpoints),
                "has_admin": any("admin" in (ep.path or "").lower() for ep in endpoints),
                "has_api": any("/api/" in (ep.path or "") for ep in endpoints),
                "has_exports": any("export" in (ep.path or "").lower() for ep in endpoints),
                "source": (target.name or "").lower(),
            })

            critical_eps = [e for e in scored_endpoints if e["risk_score"] >= 50]
            idor_candidates = [e for e in scored_endpoints if e.get("potential_idor")]
            confirmed = [v for v in verdicts if v.status == "confirmed"]

            payout_low = len(confirmed) * 500 + len(critical_eps) * 1000 + len(idor_candidates) * 500
            payout_high = len(confirmed) * 10000 + len(critical_eps) * 5000 + len(idor_candidates) * 3000
            payout_best = len(confirmed) * 25000 + len(critical_eps) * 15000 + len(idor_candidates) * 8000

            signal_quality = "high" if roi.get("quality", 0) >= 60 else ("medium" if roi.get("quality", 0) >= 30 else "low")
            findings_by_severity: Dict[str, int] = {}
            for f in findings:
                sev = f.severity or "info"
                findings_by_severity[sev] = findings_by_severity.get(sev, 0) + 1

            return {
                "target": {"id": target.id, "name": target.name, "domain": target.domain},
                "signals": {
                    "total_endpoints": len(endpoints),
                    "critical_endpoints": len(critical_eps),
                    "idor_candidates": len(idor_candidates),
                    "actionable_endpoints": sum(1 for e in scored_endpoints if e["actionable"]),
                    "confirmed_findings": len(confirmed),
                    "total_findings": len(findings),
                    "findings_by_severity": findings_by_severity,
                    "target_quality": roi.get("quality", 0),
                    "complexity": roi.get("complexity_score", 0),
                },
                "payout_estimate": {
                    "conservative_usd": payout_low,
                    "moderate_usd": payout_high,
                    "optimistic_usd": payout_best,
                    "currency": "USD",
                    "confidence": "high" if len(confirmed) >= 3 else ("medium" if len(confirmed) >= 1 else "low"),
                },
                "factors": {
                    "signal_quality": signal_quality,
                    "surface_complexity": "complex" if roi.get("complexity_score", 0) >= 50 else "moderate",
                    "has_confirmed_findings": len(confirmed) > 0,
                    "has_critical_surface": len(critical_eps) > 0,
                    "research_maturity": self._maturity_level(confirmed, scored_endpoints),
                },
                "explanation": self._generate_bounty_explanation(
                    target_name=target.name or "",
                    confirmed_count=len(confirmed),
                    critical_count=len(critical_eps),
                    idor_count=len(idor_candidates),
                    total_eps=len(endpoints),
                    payout_low=payout_low,
                    payout_high=payout_high,
                    signal_quality=signal_quality,
                    quality_score=roi.get("quality", 0),
                ),
                "recommended_focus": self._bounty_focus_recommendation(
                    confirmed=len(confirmed),
                    critical=len(critical_eps),
                    idor=len(idor_candidates),
                    actionable=sum(1 for e in scored_endpoints if e["actionable"]),
                ),
            }
        finally:
            session.close()

    def generate_daily_briefing(self) -> Dict[str, Any]:
        """Generate a complete daily investigation briefing from real system data."""
        session = db.SessionLocal()
        try:
            targets = session.query(models.Target).all()
            endpoints = session.query(models.Endpoint).all()
            findings = session.query(models.Finding).all()
            verdicts = session.query(models.Verdict).all()

            now = datetime.utcnow()
            twenty_four_hours = now - timedelta(hours=24)

            recent_endpoints = [ep for ep in endpoints if ep.discovered_at and ep.discovered_at >= twenty_four_hours]
            recent_findings = [f for f in findings if f.created_at and f.created_at >= twenty_four_hours]
            recent_verdicts = [v for v in verdicts if v.created_at and v.created_at >= twenty_four_hours]

            all_scored = []
            for ep in endpoints:
                s = unified_score(ep.path, ep.method or "GET", ep.parsed_params)
                all_scored.append(s)

            high_signal = [s for s in all_scored if s.get("risk_score", 0) >= 50]
            actionable_eps = [s for s in all_scored if s.get("actionable")]

            surfaces: Dict[str, int] = {}
            for s in all_scored:
                for surf in s.get("attack_surface", []):
                    surfaces[surf] = surfaces.get(surf, 0) + 1

            target_briefings = []
            for t in targets:
                t_eps = [ep for ep in endpoints if ep.target_id == t.id]
                t_findings = [f for f in findings if f.target_id == t.id]
                t_verdicts = [v for v in verdicts if v.endpoint_id and v.endpoint_id in {ep.id for ep in t_eps}]
                t_scored = []
                for ep in t_eps:
                    s = unified_score(ep.path, ep.method or "GET", ep.parsed_params)
                    t_scored.append(s)
                t_high = sum(1 for s in t_scored if s.get("risk_score", 0) >= 50)
                t_actionable = sum(1 for s in t_scored if s.get("actionable"))
                t_confirmed = sum(1 for v in t_verdicts if v.status == "confirmed")
                target_briefings.append({
                    "id": t.id,
                    "name": t.name,
                    "domain": t.domain,
                    "endpoints": len(t_eps),
                    "high_risk": t_high,
                    "actionable": t_actionable,
                    "findings": len(t_findings),
                    "confirmed": t_confirmed,
                    "verdicts": len(t_verdicts),
                })

            target_briefings.sort(key=lambda x: (x["confirmed"], x["high_risk"], x["actionable"]), reverse=True)

            return {
                "generated_at": now.isoformat(),
                "period": "daily",
                "system_state": {
                    "targets": len(targets),
                    "total_endpoints": len(endpoints),
                    "high_signal_endpoints": len(high_signal),
                    "actionable_endpoints": len(actionable_eps),
                    "total_findings": len(findings),
                    "total_verdicts": len(verdicts),
                },
                "recent_activity": {
                    "new_endpoints_24h": len(recent_endpoints),
                    "new_findings_24h": len(recent_findings),
                    "new_verdicts_24h": len(recent_verdicts),
                },
                "top_surfaces": [
                    {"surface": k, "count": v}
                    for k, v in sorted(surfaces.items(), key=lambda x: -x[1])[:5]
                ],
                "priority_targets": target_briefings[:5],
                "summary": self._generate_briefing_summary(
                    total_targets=len(targets),
                    total_eps=len(endpoints),
                    high_signal=len(high_signal),
                    actionable=len(actionable_eps),
                    total_findings=len(findings),
                    recent_eps=len(recent_endpoints),
                    recent_findings=len(recent_findings),
                    recent_verdicts=len(recent_verdicts),
                ),
            }
        finally:
            session.close()

    def generate_system_intelligence_report(self) -> Dict[str, Any]:
        """Generate a comprehensive system intelligence report.

        Aggregates all targets, their investigation state, verdicts,
        attack surface coverage, and opportunity scoring into a single
        intelligence-grade report.
        """
        session = db.SessionLocal()
        try:
            targets = session.query(models.Target).all()
            endpoints = session.query(models.Endpoint).all()
            verdicts = session.query(models.Verdict).all()
            findings = session.query(models.Finding).all()

            ep_map: Dict[int, List[models.Endpoint]] = {}
            for ep in endpoints:
                tid = ep.target_id or 0
                ep_map.setdefault(tid, []).append(ep)

            f_map: Dict[int, List[models.Finding]] = {}
            for f in findings:
                tid = f.target_id or 0
                f_map.setdefault(tid, []).append(f)

            v_map: Dict[int, List[models.Verdict]] = {}
            for v in verdicts:
                eid = v.endpoint_id
                if eid:
                    for tid, eps in ep_map.items():
                        if any(ep.id == eid for ep in eps):
                            v_map.setdefault(tid, []).append(v)
                            break

            total_actionable = 0
            total_high_risk = 0
            total_confirmed = 0
            top_targets = []

            for t in targets:
                tid = t.id
                t_eps = ep_map.get(tid, [])
                t_findings = f_map.get(tid, [])
                t_verdicts = v_map.get(tid, [])

                scored = []
                for ep in t_eps:
                    s = unified_score(ep.path, ep.method or "GET", ep.parsed_params)
                    scored.append(s)

                high_risk = sum(1 for s in scored if s.get("risk_score", 0) >= 50)
                actionable = sum(1 for s in scored if s.get("actionable"))
                confirmed = sum(1 for v in t_verdicts if v.status == "confirmed")

                total_actionable += actionable
                total_high_risk += high_risk
                total_confirmed += confirmed

                if t_eps:
                    surfaces: Dict[str, int] = {}
                    for s in scored:
                        for surf in s.get("attack_surface", []):
                            surfaces[surf] = surfaces.get(surf, 0) + 1
                    top_surface = max(surfaces, key=surfaces.get) if surfaces else "none"
                else:
                    top_surface = "none"

                roi = unified_score_target({
                    "api_count": len(t_eps),
                    "has_graphql": any("/graphql" in (ep.path or "").lower() for ep in t_eps),
                    "has_admin": any("admin" in (ep.path or "").lower() for ep in t_eps),
                    "has_api": any("/api/" in (ep.path or "") for ep in t_eps),
                    "has_exports": any("export" in (ep.path or "").lower() for ep in t_eps),
                    "source": (t.name or "").lower(),
                })

                top_targets.append({
                    "target_id": t.id,
                    "name": t.name,
                    "domain": t.domain,
                    "endpoints": len(t_eps),
                    "high_risk_endpoints": high_risk,
                    "actionable_endpoints": actionable,
                    "findings": len(t_findings),
                    "confirmed_verdicts": confirmed,
                    "top_surface": top_surface,
                    "roi_score": roi.get("roi_score", 0),
                    "quality_score": roi.get("quality", 0),
                    "priority_score": roi.get("priority", 0),
                    "complexity_score": roi.get("complexity_score", 0),
                })

            top_targets.sort(key=lambda x: (x["priority_score"], x["confirmed_verdicts"]), reverse=True)
            total_payout_low = sum(t["confirmed_verdicts"] * 500 + t["high_risk_endpoints"] * 1000 for t in top_targets)
            total_payout_high = sum(t["confirmed_verdicts"] * 10000 + t["high_risk_endpoints"] * 5000 for t in top_targets)

            return {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "scope": "full_system",
                "coverage": {
                    "total_targets": len(targets),
                    "total_endpoints": len(endpoints),
                    "total_findings": len(findings),
                    "total_verdicts": len(verdicts),
                    "total_actionable": total_actionable,
                    "total_high_risk": total_high_risk,
                    "total_confirmed_verdicts": total_confirmed,
                    "targets_with_coverage": sum(1 for t in targets if ep_map.get(t.id)),
                    "targets_with_findings": sum(1 for t in targets if f_map.get(t.id)),
                },
                "bounty_potential": {
                    "conservative_usd": total_payout_low,
                    "moderate_usd": total_payout_high,
                    "currency": "USD",
                },
                "top_targets": top_targets[:10],
                "recommended_priority": self._recommend_system_priority(top_targets),
            }
        finally:
            session.close()

    def _interpret_state(
        self,
        target: models.Target,
        scored_endpoints: List[Dict[str, Any]],
        verdicts: List[models.Verdict],
        findings: List[models.Finding],
    ) -> Dict[str, Any]:
        confirmed = [v for v in verdicts if v.status == "confirmed"]
        high_risk = [e for e in scored_endpoints if e["risk_score"] >= 50]
        actionable = [e for e in scored_endpoints if e.get("actionable")]

        if not scored_endpoints:
            narrative = f"{target.name} has no endpoints analyzed yet. Run a scan to begin investigation."
            focus = "scan"
        elif not confirmed:
            narrative = (
                f"{target.name} has {len(scored_endpoints)} endpoints ({len(high_risk)} high risk, "
                f"{len(actionable)} actionable) but no confirmed findings. "
                f"Begin validation on high-risk endpoints to identify vulnerabilities."
            )
            focus = "validate"
        elif confirmed:
            confirmed_high = [v for v in confirmed if self._parse_conf(v.confidence) >= 0.7]
            narrative = (
                f"{target.name} has {len(confirmed)} confirmed findings "
                f"({len(confirmed_high)} with confidence >= 70%). "
                f"{len(high_risk)} high-risk endpoints remain unexplored. "
                f"Generate reports for confirmed findings and continue validation."
            )
            focus = "report" if len(confirmed) >= 2 else "validate"

        return {
            "narrative": narrative,
            "focus": focus,
            "phase": "discovery" if not scored_endpoints else (
                "exploitation" if confirmed else "validation"
            ),
            "risk_level": risk_to_severity(
                sum(e["risk_score"] for e in scored_endpoints) / len(scored_endpoints)
                if scored_endpoints else 0
            ),
        }

    def _format_narrative_output(self, report: FinalReport, target_name: str) -> Dict[str, Any]:
        return {
            "hot_path_id": report.verdict_id,
            "status": "ready",
            "title": report.title,
            "severity": report.severity,
            "cvss": report.cvss,
            "affected_endpoint": report.affected_endpoint,
            "attack_vector": report.attack_vector,
            "narrative": report.narrative,
            "reproduction_steps": report.reproduction_steps,
            "remediation": report.remediation,
            "poc_curl": report.poc_curl,
            "bounty_estimate": report.bounty_estimate,
            "evidence_count": len(report.evidence),
            "export_formats_available": list(report.export_formats.keys()),
            "target_name": target_name,
        }

    def _estimate_bounty_range(self, verdicts: List[models.Verdict]) -> str:
        max_confidence = max((self._parse_conf(v.confidence) for v in verdicts), default=0.0)
        if max_confidence >= 0.9:
            return "$2,000 - $25,000"
        if max_confidence >= 0.7:
            return "$1,000 - $10,000"
        return "$500 - $5,000"

    def _describe_path_type(self, path_type: str) -> str:
        descriptions = {
            "idor": "Insecure Direct Object Reference path — endpoints handling object IDs without proper authorization",
            "auth": "Authentication-related path — endpoints involved in authentication or session management",
            "data": "Data exposure path — endpoints that may leak sensitive information across contexts",
            "web3": "Web3/Crypto path — smart contract, wallet, or blockchain RPC endpoints",
            "graphql": "GraphQL attack surface — query/mutation endpoints with complex authorization logic",
            "admin": "Admin privilege path — administrative endpoints that may be accessible without proper role checks",
            "api": "API-level path — RESTful endpoints processing user-controlled input",
        }
        return descriptions.get(path_type, f"Investigation path of type '{path_type}'")

    def _generate_path_explanation(
        self,
        path_type: str,
        path_value: str,
        high_risk_count: int,
        confirmed_count: int,
        surfaces: Dict[str, int],
    ) -> str:
        parts = [
            f"Attack path '{path_value}' (type: {path_type}) includes {high_risk_count} high-risk "
            f"endpoints and {confirmed_count} confirmed findings."
        ]
        if surfaces:
            top = max(surfaces, key=surfaces.get)
            parts.append(f"Dominant attack surface: {top} ({surfaces[top]} endpoints).")
        if confirmed_count > 0:
            parts.append(f"Validated exploitation possible — {confirmed_count} verdicts confirmed.")
        else:
            parts.append("No confirmed verdicts yet — prioritize validation on high-risk endpoints.")
        return " ".join(parts)

    def _recommend_path_action(
        self,
        confirmed_count: int,
        high_risk_count: int,
        actionable_count: int,
    ) -> Dict[str, Any]:
        if confirmed_count > 0:
            return {
                "action": "Generate reports for confirmed findings and continue probing actionable endpoints",
                "priority": "high",
                "estimated_effort": f"{actionable_count * 15} min for remaining endpoints",
            }
        if high_risk_count > 0:
            return {
                "action": "Run validation on high-risk endpoints to identify vulnerabilities",
                "priority": "high",
                "estimated_effort": f"{high_risk_count * 20} min for validation",
            }
        return {
            "action": "Increase coverage — add more endpoints or run additional scans",
            "priority": "medium",
            "estimated_effort": "Depends on target scope",
        }

    def _top_vectors(self, endpoints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        counts: Dict[str, int] = {}
        for e in endpoints:
            vec = e.get("vector", "unknown")
            counts[vec] = counts.get(vec, 0) + 1
        return [
            {"vector": k, "count": v}
            for k, v in sorted(counts.items(), key=lambda x: -x[1])
        ]

    def _top_signals(self, endpoints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        counts: Dict[str, int] = {}
        for e in endpoints:
            for sig in e.get("signals", []):
                counts[sig] = counts.get(sig, 0) + 1
        return [
            {"signal": k, "count": v}
            for k, v in sorted(counts.items(), key=lambda x: -x[1])[:5]
        ]

    def _generate_unified_narrative(
        self,
        target_name: str,
        web2_count: int,
        web3_count: int,
        web2_high_risk: int,
        web3_high_risk: int,
        web3_findings: int,
        web3_verdicts: int,
    ) -> str:
        parts = [f"Analysis of {target_name} reveals a hybrid Web2+Web3 attack surface."]
        parts.append(
            f"Web2: {web2_count} endpoints ({web2_high_risk} high risk). "
            f"Web3: {web3_count} endpoints ({web3_high_risk} high risk, "
            f"{web3_findings} findings, {web3_verdicts} verdicts)."
        )
        if web3_count > 0 and web2_count > 0:
            parts.append(
                "The presence of both traditional API endpoints and Web3 surfaces "
                "creates unique attack chains where blockchain interactions can be "
                "combined with API-level vulnerabilities."
            )
            if web3_verdicts > 0:
                parts.append(f"Web3 validation has produced {web3_verdicts} verdicts — "
                             f"smart contract or RPC-level issues are confirmed.")
        elif web3_count > 0:
            parts.append("Focus on Web3-specific attack vectors: signature validation, "
                         "RPC endpoint hardening, and smart contract interaction patterns.")
        else:
            parts.append("No Web3 surface detected. All endpoints are traditional Web2 API surfaces.")

        return " ".join(parts)

    def _merge_surfaces(self, web2: List[Dict], web3: List[Dict]) -> List[Dict[str, Any]]:
        merged: Dict[str, int] = {}
        for e in web2 + web3:
            for s in e.get("surfaces", []):
                merged[s] = merged.get(s, 0) + 1
        return [
            {"surface": k, "count": v, "domain": "web3" if any(
                k in (we.get("surfaces", []) or []) for we in web3
            ) else "web2"}
            for k, v in sorted(merged.items(), key=lambda x: -x[1])
        ]

    def _generate_bounty_explanation(
        self,
        target_name: str,
        confirmed_count: int,
        critical_count: int,
        idor_count: int,
        total_eps: int,
        payout_low: int,
        payout_high: int,
        signal_quality: str,
        quality_score: float,
    ) -> str:
        parts = [
            f"Bounty potential for {target_name} is estimated between ${payout_low:,} and ${payout_high:,}."
        ]
        parts.append(f"Signals: {confirmed_count} confirmed findings, {critical_count} critical-risk "
                     f"endpoints, {idor_count} IDOR candidates across {total_eps} total endpoints.")
        parts.append(f"Signal quality: {signal_quality} (score: {quality_score:.0f}/100).")
        if confirmed_count > 0:
            parts.append(f"With {confirmed_count} confirmed findings, you already have "
                         f"evidence that can be converted into paid reports.")
        if critical_count > 0:
            parts.append(f"The {critical_count} critical-risk endpoints represent "
                         f"high-value targets for Critical/High severity submissions.")
        return " ".join(parts)

    def _bounty_focus_recommendation(
        self,
        confirmed: int,
        critical: int,
        idor: int,
        actionable: int,
    ) -> str:
        if confirmed >= 3:
            return f"Focus on writing and submitting reports for {confirmed} confirmed findings. Continue validation on {actionable} actionable endpoints."
        if critical > 0:
            return f"Validate {critical} critical-risk endpoints — these represent the highest bounty potential."
        if idor > 0:
            return f"Prioritize {idor} IDOR candidates — they often yield Medium-High severity payouts."
        if actionable > 0:
            return f"Investigate {actionable} actionable endpoints to discover new findings."
        return "Increase endpoint coverage through scanning to identify attack surface."

    def _maturity_level(
        self,
        confirmed: List[models.Verdict],
        scored_endpoints: List[Dict[str, Any]],
    ) -> str:
        if len(confirmed) >= 5:
            return "mature"
        if len(confirmed) >= 2:
            return "developing"
        if len(confirmed) >= 1:
            return "initial"
        if any(e.get("actionable") for e in scored_endpoints):
            return "exploring"
        return "uncharted"

    def _generate_briefing_summary(
        self,
        total_targets: int,
        total_eps: int,
        high_signal: int,
        actionable: int,
        total_findings: int,
        recent_eps: int,
        recent_findings: int,
        recent_verdicts: int,
    ) -> str:
        parts = [
            f"System spans {total_targets} targets with {total_eps} endpoints "
            f"({high_signal} high signal, {actionable} actionable)."
        ]
        activity_parts = []
        if recent_eps > 0:
            activity_parts.append(f"{recent_eps} new endpoints")
        if recent_findings > 0:
            activity_parts.append(f"{recent_findings} new findings")
        if recent_verdicts > 0:
            activity_parts.append(f"{recent_verdicts} new verdicts")

        if activity_parts:
            parts.append(f"Recent activity (24h): {' + '.join(activity_parts)}.")
        else:
            parts.append("No activity in the last 24 hours.")

        if actionable > 0:
            parts.append(f"Recommended: investigate {actionable} actionable endpoints "
                         f"and generate reports for confirmed findings.")
        else:
            parts.append("Recommended: run scans to increase coverage and identify actionable surfaces.")

        parts.append(f"Total findings across all targets: {total_findings}.")
        return " ".join(parts)

    def _recommend_system_priority(self, top_targets: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not top_targets:
            return {"focus": "expansion", "reason": "No targets with coverage. Add targets and run scans."}

        best = top_targets[0]
        if best.get("confirmed_verdicts", 0) > 0:
            return {
                "focus": "submission",
                "target_name": best["name"],
                "target_id": best["target_id"],
                "reason": f"{best['name']} has {best['confirmed_verdicts']} confirmed findings ready for report generation.",
            }
        if best.get("high_risk_endpoints", 0) > 0:
            return {
                "focus": "validation",
                "target_name": best["name"],
                "target_id": best["target_id"],
                "reason": f"{best['name']} has {best['high_risk_endpoints']} high-risk endpoints requiring validation.",
            }
        return {
            "focus": "exploration",
            "target_name": best["name"],
            "target_id": best["target_id"],
            "reason": f"{best['name']} has {best['endpoints']} endpoints. Run validation to identify findings.",
        }


_narrator_instance: Optional[InvestigationNarrator] = None


def get_narrator() -> InvestigationNarrator:
    global _narrator_instance
    if _narrator_instance is None:
        _narrator_instance = InvestigationNarrator()
    return _narrator_instance
