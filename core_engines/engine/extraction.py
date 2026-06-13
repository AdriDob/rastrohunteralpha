from typing import Any, Dict, List, Optional


def extract_endpoints(snapshot) -> List[Dict[str, Any]]:
    if snapshot is None:
        return []
    out = []
    for ep in getattr(snapshot, "endpoints", []):
        out.append({
            "path": getattr(ep, "path", "/"),
            "method": getattr(ep, "method", "GET"),
            "risk_score": getattr(ep, "risk_score", 0.0),
            "confidence": getattr(ep, "confidence", 0.0),
            "labels": list(getattr(ep, "labels", [])),
            "attack_surface": list(getattr(ep, "attack_surface", [])),
            "signals": list(getattr(ep, "signals", [])),
            "vector": getattr(ep, "vector", ""),
            "potential_idor": getattr(ep, "potential_idor", False),
            "actionable": getattr(ep, "actionable", False),
        })
    return out


def extract_hot_paths(snapshot, hot_paths: Optional[List] = None, investigation_graph=None) -> List[Dict[str, Any]]:
    out = []
    src = investigation_graph or hot_paths
    if src is not None:
        items = getattr(src, "hot_paths", src) if investigation_graph is not None else src
        for item in items:
            if hasattr(item, "nodes"):
                out.append({
                    "nodes": list(getattr(item, "nodes", [])),
                    "why_it_matters": getattr(item, "why_it_matters", ""),
                    "estimated_reward": getattr(item, "estimated_reward", "medium"),
                })
            elif isinstance(item, dict):
                out.append(item)
    if not out and snapshot is not None:
        for hp in getattr(snapshot, "hot_paths", []):
            out.append({
                "node_id": getattr(hp, "node_id", ""),
                "path": getattr(hp, "path", ""),
                "method": getattr(hp, "method", "GET"),
                "risk_score": getattr(hp, "risk_score", 0.0),
                "vector": getattr(hp, "vector", ""),
                "cluster_type": getattr(hp, "cluster_type", None),
            })
    return out


def extract_verdict_map(snapshot, verdicts: Optional[List] = None, evidence_graph=None) -> Dict[str, Dict[str, Any]]:
    vd_map: Dict[str, Dict[str, Any]] = {}

    if verdicts:
        for v in verdicts:
            hot_path_id = getattr(v, "hot_path_id", "")
            vd_map[hot_path_id] = {
                "hot_path_id": hot_path_id,
                "status": getattr(v, "status", "unknown"),
                "confidence": getattr(v, "confidence", 0.0),
                "reproducibility_score": getattr(v, "reproducibility_score", 0.0),
                "reason": getattr(v, "reason", ""),
            }

    if not vd_map and snapshot is not None:
        for v in getattr(snapshot, "verdicts", []):
            hpid = getattr(v, "hot_path_id", "")
            vd_map[hpid] = {
                "hot_path_id": hpid,
                "status": getattr(v, "status", "unknown"),
                "confidence": getattr(v, "confidence", 0.0),
                "reproducibility_score": getattr(v, "reproducibility_score", 0.0),
            }

    if not vd_map and evidence_graph is not None:
        for nd in evidence_graph.get_verdicts():
            hpid = nd.get("hot_path_id", "")
            vd_map[hpid] = {
                "hot_path_id": hpid,
                "status": nd.get("status", "unknown"),
                "confidence": nd.get("confidence", 0.0),
                "reproducibility_score": nd.get("reproducibility_score", 0.0),
                "reason": nd.get("reason", ""),
                "passed_rules": nd.get("passed_rules", []),
                "failed_rules": nd.get("failed_rules", []),
            }

    return vd_map


def extract_surface(attack_surface, snapshot) -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = {
        "idor_clusters": [], "auth_boundaries": [],
        "multi_tenant_zones": [], "graphql_surfaces": [],
    }
    if attack_surface is not None:
        for attr in ("idor_clusters", "auth_boundaries", "multi_tenant_zones", "graphql_surfaces"):
            if hasattr(attack_surface, attr):
                out[attr] = list(getattr(attack_surface, attr))
    if snapshot is not None:
        ss = getattr(snapshot, "attack_surface", None)
        if ss is not None:
            for attr in ("idor_clusters", "auth_boundaries", "multi_tenant_zones", "graphql_surfaces"):
                if not out[attr]:
                    out[attr] = list(getattr(ss, attr, []))
    return out


def extract_quick_wins(quick_wins) -> Dict[str, Any]:
    if quick_wins is None:
        return {}
    out: Dict[str, Any] = {
        "top_quick_wins": [], "fast_exploit_paths": [],
        "low_effort_high_roi": [], "total_estimated_value": 0.0,
        "avg_quick_win_score": 0.0,
    }
    if hasattr(quick_wins, "top_quick_wins"):
        out["top_quick_wins"] = [
            {
                "endpoint_path": getattr(w, "endpoint_path", ""),
                "endpoint_method": getattr(w, "endpoint_method", ""),
                "roi_score": getattr(w, "roi_score", 0.0),
                "quick_win_score": getattr(w, "quick_win_score", 0.0),
                "estimated_payout": getattr(w, "estimated_payout", 0.0),
                "category": getattr(w, "category", ""),
                "reasoning": getattr(w, "reasoning", ""),
            }
            for w in quick_wins.top_quick_wins
        ]
    if hasattr(quick_wins, "fast_exploit_paths"):
        out["fast_exploit_paths"] = [
            {
                "entry_endpoint": getattr(p, "entry_endpoint", ""),
                "vulnerability_type": getattr(p, "vulnerability_type", ""),
                "chain_length": getattr(p, "chain_length", 0),
            }
            for p in quick_wins.fast_exploit_paths
        ]
    if hasattr(quick_wins, "low_effort_high_roi_targets"):
        out["low_effort_high_roi"] = [
            {
                "endpoint_path": getattr(t, "endpoint_path", ""),
                "roi_score": getattr(t, "roi_score", 0.0),
            }
            for t in quick_wins.low_effort_high_roi_targets
        ]
    if hasattr(quick_wins, "total_estimated_value"):
        out["total_estimated_value"] = quick_wins.total_estimated_value
    if hasattr(quick_wins, "avg_quick_win_score"):
        out["avg_quick_win_score"] = quick_wins.avg_quick_win_score
    return out
