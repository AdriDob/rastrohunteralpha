"""
Quick Wins Engine — Monetization Prioritization Layer.

NOT a scanner, hypothesis generator, or reporting system.
This is a prioritization overlay that ranks EXISTING pipeline outputs
by expected speed-to-payout. It NEVER generates new data.

Anti-drift governance (HARD CONSTRAINTS):
- Hypotheses ≠ Findings (never promote predictions to facts)
- ROI predicted ≠ ROI confirmed (pipeline ROI is NOT evidence)
- Surface expansion ≠ discovered endpoints
- AI Assistant MUST NOT consume Quick Wins as truth
- Evidence = truth. Verdicts = truth validation. Pipeline = execution reality.
- Quick Wins = prioritization overlay ONLY.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.quick_wins.models import (
    FastExploitPath,
    ImmediateActionEndpoint,
    LowEffortHighRoi,
    QuickWin,
    QuickWinsReport,
)

LOG = logging.getLogger("rastro.quick_wins")


class QuickWinsEngine:
    def __init__(self):
        pass

    def evaluate(
        self,
        snapshot,
        evidence_graph=None,
    ) -> QuickWinsReport:
        endpoints = list(getattr(snapshot, "endpoints", []))
        hot_paths = list(getattr(snapshot, "hot_paths", []))
        verdicts = list(getattr(snapshot, "verdicts", []))
        reports = list(getattr(snapshot, "reports", []))
        surface = getattr(snapshot, "attack_surface", None)
        target = getattr(snapshot, "target", None)
        target_name = getattr(target, "name", "unknown") if target else "unknown"

        evidence_nodes = []
        evidence_edges = []
        if evidence_graph is not None:
            evidence_nodes = evidence_graph.get_verdicts()
            evidence_edges = evidence_graph.get_edges()

        # Build lookup maps from truth-layer data only
        verdict_map = self._build_verdict_map(verdicts)
        reported_endpoints = set(r.affected_endpoint for r in reports)

        # ── 1. Score every endpoint as a potential quick win ──
        all_wins: List[QuickWin] = []
        for ep in endpoints:
            ep_verdict = verdict_map.get(ep.path)
            win = self._score_endpoint(
                ep, ep_verdict, reported_endpoints, evidence_nodes,
            )
            if win is not None:
                all_wins.append(win)

        # Sort descending by quick_win_score
        all_wins.sort(key=lambda w: w.quick_win_score, reverse=True)

        # ── 2. Classify into categories ──
        ready = [w for w in all_wins if w.category == "ready_to_report"]
        half_confirmed = [w for w in all_wins if w.category == "half_confirmed"]
        low_hanging = [w for w in all_wins if w.category == "low_hanging_fruit"]
        underexplored = [w for w in all_wins if w.category == "underexplored"]

        top_10 = all_wins[:10]

        # ── 3. Fast exploit paths from confirmed verdicts + evidence ──
        fast_paths = self._build_fast_exploit_paths(
            ready, hot_paths, evidence_edges,
        )

        # ── 4. Low-effort high-ROI targets ──
        low_effort_targets = self._build_low_effort_targets(low_hanging, underexplored)

        # ── 5. Immediate action endpoints ──
        immediate = self._build_immediate_actions(ready, half_confirmed)

        # ── 6. Confidence-ranked opportunities ──
        ranked = sorted(all_wins, key=lambda w: w.confidence_score, reverse=True)

        # ── Aggregate metrics ──
        n = len(all_wins)
        avg_score = sum(w.quick_win_score for w in all_wins) / max(n, 1)
        fastest = min(
            (w for w in ready if w.estimated_effort_minutes > 0),
            key=lambda w: w.estimated_effort_minutes,
            default=None,
        )

        return QuickWinsReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
            target_name=target_name,
            top_quick_wins=top_10,
            fast_exploit_paths=fast_paths,
            low_effort_high_roi_targets=low_effort_targets,
            immediate_action_endpoints=immediate,
            confidence_ranked_opportunities=ranked[:20],
            total_opportunities=n,
            avg_quick_win_score=round(avg_score, 3),
            exploitability_score=round(
                sum(w.exploitability_score for w in all_wins) / max(n, 1), 3
            ),
            fastest_path_minutes=getattr(fastest, "estimated_effort_minutes", 0),
            total_estimated_value=sum(w.estimated_payout for w in all_wins),
        )

    # ── Scoring methods ──────────────────────────────────────

    def _score_endpoint(
        self,
        ep,
        verdict,
        reported_endpoints: set,
        evidence_nodes: List[Dict],
    ) -> Optional[QuickWin]:
        path = getattr(ep, "path", "/")
        method = getattr(ep, "method", "GET")
        risk_score = getattr(ep, "risk_score", 0.0)
        signals = list(getattr(ep, "signals", []))
        labels = list(getattr(ep, "labels", []))
        surface = list(getattr(ep, "attack_surface", []))
        vector = getattr(ep, "vector", "")
        actionable = getattr(ep, "actionable", False)
        potential_idor = getattr(ep, "potential_idor", False)

        # Skip endpoints already reported — they're done
        if path in reported_endpoints:
            return None

        # ── ROI score — from truth layer only ──
        roi_score = self._compute_roi(risk_score, vector, signals, surface, potential_idor)

        # ── Confidence score — from verdicts + evidence ──
        confidence_score = 0.0
        verdict_status = None
        verdict_confidence_val = None
        reproducibility = None
        evidence_count = 0

        if verdict is not None:
            verdict_status = getattr(verdict, "status", "unknown")
            verdict_confidence_val = getattr(verdict, "confidence", 0.0)
            reproducibility = getattr(verdict, "reproducibility_score", None)
            confidence_score = self._compute_confidence(
                verdict_status, verdict_confidence_val,
            )

        # Evidence consistency bonus
        for nd in evidence_nodes:
            if nd.get("hot_path_id", "").endswith(path):
                evidence_count += 1
                if nd.get("consistent") and confidence_score < 1.0:
                    confidence_score = min(confidence_score + 0.05, 1.0)

        # ── Exploitability score ──
        exploitability_score = self._compute_exploitability(method, labels, vector)

        # ── Complexity score ──
        complexity_score = self._compute_complexity(
            risk_score, signals, potential_idor, evidence_count,
        )

        # ── Blend into quick-win score ──
        quick_win_score = (
            roi_score * 0.4
            + confidence_score * 0.3
            + exploitability_score * 0.2
            - complexity_score * 0.3
        )
        quick_win_score = max(0.0, min(1.0, quick_win_score))

        # ── Classify ──
        category, reasoning, signals_list = self._classify(
            quick_win_score, confidence_score, verdict_status,
            risk_score, evidence_count,
        )

        # Effort estimate
        effort_minutes = self._estimate_effort(method, complexity_score, evidence_count, verdict_status)

        # Payout estimate
        payout = self._estimate_payout(risk_score, vector, potential_idor)

        return QuickWin(
            endpoint_path=path,
            endpoint_method=method,
            quick_win_score=round(quick_win_score, 3),
            roi_score=round(roi_score, 3),
            confidence_score=round(confidence_score, 3),
            exploitability_score=round(exploitability_score, 3),
            complexity_score=round(complexity_score, 3),
            category=category,
            reasoning=reasoning,
            supporting_signals=signals_list,
            estimated_payout=round(payout, 2),
            estimated_effort_minutes=effort_minutes,
            verdict_status=verdict_status,
            verdict_confidence=verdict_confidence_val,
            evidence_count=evidence_count,
            reproducibility_score=reproducibility,
        )

    def _compute_roi(
        self,
        risk_score: float,
        vector: str,
        signals: List[str],
        surface: List[str],
        potential_idor: bool,
    ) -> float:
        base = risk_score / 100.0
        payout_multipliers = {
            "IDOR": 1.0,
            "Privilege escalation": 0.9,
            "Auth bypass": 0.85,
            "Data exposure": 0.7,
            "GraphQL logic": 0.75,
            "Business logic": 0.5,
        }
        multiplier = payout_multipliers.get(vector, 0.3)
        data_sensitivity = 0.0
        if potential_idor:
            data_sensitivity += 0.2
        if "export" in signals or "data_exfiltration" in surface:
            data_sensitivity += 0.2
        if "billing" in signals:
            data_sensitivity += 0.2
        if "admin" in signals:
            data_sensitivity += 0.1
        roi = min(base * multiplier + data_sensitivity, 1.0)
        return roi

    def _compute_confidence(
        self, status: str, confidence_val: float,
    ) -> float:
        if status == "confirmed":
            return min(confidence_val + 0.2, 1.0)
        if status == "inconclusive":
            return confidence_val * 0.5
        return 0.0

    def _compute_exploitability(
        self, method: str, labels: List[str], vector: str,
    ) -> float:
        score = 0.0
        m = method.upper()
        if m in ("GET",):
            score += 0.6
        elif m in ("POST", "PUT", "PATCH"):
            score += 0.7
        elif m == "DELETE":
            score += 0.4
        if "auth" not in labels:
            score += 0.3
        if vector in ("IDOR", "GraphQL logic", "Auth bypass"):
            score += 0.2
        if "graphql" in labels:
            score += 0.1
        return min(score, 1.0)

    def _compute_complexity(
        self,
        risk_score: float,
        signals: List[str],
        potential_idor: bool,
        evidence_count: int,
    ) -> float:
        base = 1.0 - (risk_score / 100.0)
        if potential_idor:
            base -= 0.1
        if "auth" in signals or "authentication_surface" in signals:
            base += 0.2
        if evidence_count >= 3:
            base -= 0.15
        return max(0.0, min(base, 1.0))

    def _classify(
        self,
        score: float,
        confidence_score: float,
        verdict_status,
        risk_score: float,
        evidence_count: int,
    ) -> tuple:
        if verdict_status == "confirmed" and confidence_score >= 0.6:
            return (
                "ready_to_report",
                "Confirmed finding with high confidence — immediately actionable",
                ["verdict_confirmed", f"confidence_{confidence_score:.2f}"],
            )
        if verdict_status == "inconclusive" and risk_score >= 50 and evidence_count > 0:
            return (
                "half_confirmed",
                f"Strong signals but only partially validated ({evidence_count} evidence records)",
                ["inconclusive_verdict", f"evidence_{evidence_count}"],
            )
        if score >= 0.5 and risk_score >= 50:
            return (
                "low_hanging_fruit",
                "High ROI with low complexity — minimal effort for likely payout",
                [f"quick_win_score_{score:.2f}", f"risk_{risk_score:.0f}"],
            )
        return (
            "underexplored",
            f"High scoring endpoint with limited validation — potential missed opportunity",
            [f"risk_{risk_score:.0f}"],
        )

    def _estimate_effort(
        self,
        method: str,
        complexity: float,
        evidence_count: int,
        verdict_status,
    ) -> int:
        if verdict_status == "confirmed":
            return 15 + int(complexity * 30)
        if evidence_count >= 3:
            return 30 + int(complexity * 45)
        m = method.upper()
        base = 30 if m in ("GET",) else 60
        return base + int(complexity * 60)

    def _estimate_payout(
        self,
        risk_score: float,
        vector: str,
        potential_idor: bool,
    ) -> float:
        base = risk_score / 100.0 * 5000
        if vector in ("IDOR", "Privilege escalation", "Auth bypass"):
            base *= 1.5
        if potential_idor:
            base *= 1.3
        if "export" in vector.lower() or "data" in vector.lower():
            base *= 1.2
        return base

    # ── Builders ──────────────────────────────────────────────

    def _build_verdict_map(self, verdicts) -> Dict[str, Any]:
        m: Dict[str, Any] = {}
        for v in verdicts:
            hpid = getattr(v, "hot_path_id", "")
            if ":" in hpid:
                path = hpid.split(":", 1)[1]
                m[path] = v
        return m

    def _build_fast_exploit_paths(
        self,
        ready_wins: List[QuickWin],
        hot_paths,
        evidence_edges: List[Dict],
    ) -> List[FastExploitPath]:
        paths: List[FastExploitPath] = []
        for win in ready_wins[:5]:
            evidence_steps = [
                f"{win.endpoint_method} {win.endpoint_path} — confirmed verdict"
            ]
            for edge in evidence_edges[:3]:
                if win.endpoint_path in edge.get("from", "") or win.endpoint_path in edge.get("to", ""):
                    evidence_steps.append(
                        f"evidence: {edge.get('from')} → {edge.get('to')} ({edge.get('relationship')})"
                    )
            paths.append(FastExploitPath(
                entry_endpoint=win.endpoint_path,
                entry_method=win.endpoint_method,
                chain_length=len(evidence_steps),
                vulnerability_type=win.reason.split("—")[-1].strip() if "—" in win.reason else "unknown",
                payout_likelihood=win.quick_win_score,
                evidence_steps=evidence_steps[:5],
                impact_summary=win.reasoning,
                path_id=f"qw_fast_{win.endpoint_path.replace('/', '_')[:40]}",
            ))
        return paths

    def _build_low_effort_targets(
        self,
        low_hanging: List[QuickWin],
        underexplored: List[QuickWin],
    ) -> List[LowEffortHighRoi]:
        targets: List[LowEffortHighRoi] = []
        combined = low_hanging[:5] + underexplored[:3]
        for win in combined:
            is_partial = win.verdict_status == "inconclusive"
            is_under = win.category == "underexplored"
            targets.append(LowEffortHighRoi(
                target_name="",
                endpoint_path=win.endpoint_path,
                endpoint_method=win.endpoint_method,
                roi_score=win.roi_score,
                complexity_score=win.complexity_score,
                effort_estimate_minutes=win.estimated_effort_minutes,
                reason=win.reasoning,
                is_partially_confirmed=is_partial,
                is_underexplored=is_under,
            ))
        return targets

    def _build_immediate_actions(
        self,
        ready: List[QuickWin],
        half_confirmed: List[QuickWin],
    ) -> List[ImmediateActionEndpoint]:
        actions: List[ImmediateActionEndpoint] = []
        for win in ready[:5]:
            steps = [
                f"Review evidence for {win.endpoint_method} {win.endpoint_path}",
                "Verify reproducibility with manual request",
                "Write report body with proof of concept",
            ]
            if win.reproducibility_score and win.reproducibility_score < 0.8:
                steps.insert(1, f"Confirm reproducibility (current: {win.reproducibility_score:.2f})")

            actions.append(ImmediateActionEndpoint(
                path=win.endpoint_path,
                method=win.endpoint_method,
                action="write_report",
                priority="high",
                confidence=win.quick_win_score,
                risk_score=win.roi_score,
                reason=win.reasoning,
                steps=steps,
            ))

        for win in half_confirmed[:3]:
            steps = [
                f"Manually validate {win.endpoint_method} {win.endpoint_path}",
                "Send probe request with modified parameters",
                "If confirmed, proceed to report",
            ]

            actions.append(ImmediateActionEndpoint(
                path=win.endpoint_path,
                method=win.endpoint_method,
                action="manual_validation",
                priority="medium",
                confidence=win.confidence_score,
                risk_score=win.roi_score,
                reason=win.reasoning,
                steps=steps,
            ))

        return actions
