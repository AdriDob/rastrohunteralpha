import logging
import re
from collections.abc import Iterable
from typing import Any

logger = logging.getLogger("rastro.attack.engine")

from core_engines.engine.unified_scoring import generate_suggestions as unified_suggestions
from core_engines.engine.unified_scoring import score as unified_score

OBJECT_REFERENCE_TOKENS = [
    "user_id",
    "uid",
    "account_id",
    "order_id",
    "invoice_id",
    "device_id",
    "file_id",
    "customer_id",
    "subscription_id",
    "team_id",
    "project_id",
    "resource_id",
    "session_id",
]

OWNERSHIP_HINTS = [
    "user",
    "account",
    "profile",
    "order",
    "invoice",
    "subscription",
    "device",
    "tenant",
    "org",
    "project",
    "team",
    "resource",
    "member",
]

SENSITIVE_PATHS = [
    "admin",
    "dashboard",
    "export",
    "download",
    "settings",
    "profile",
    "billing",
    "payment",
    "transfer",
    "report",
]

LOW_VALUE_PATTERNS = [
    r"/health",
    r"/status",
    r"/metrics",
    r"/favicon\.ico",
    r"/robots\.txt",
    r"/sitemap\.xml",
    r"/static/",
    r"/assets/",
    r"/css/",
    r"/js/",
    r"/images/",
    r"/logo",
    r"/ping",
]

ID_PATTERN = re.compile(r"(?:user|account|order|invoice|device|file|customer|subscription|team|project|resource)_?id", re.I)
NOUN_ID_PATTERN = re.compile(r"/(?:[A-Za-z]+)-?(?:id|uuid|key|token)(?:/|$)", re.I)
PATH_PARAM_PATTERN = re.compile(r"\{?[A-Za-z0-9_]+\}?")


class AttackDecisionEngine:
    def __init__(self):
        logger.debug("AttackDecisionEngine initialized")

    def is_low_value(self, path: str) -> bool:
        lower = path.lower()
        return any(re.search(pattern, lower) for pattern in LOW_VALUE_PATTERNS)

    def detect_object_reference(self, path: str, params: dict[str, Any]) -> bool:
        if ID_PATTERN.search(path):
            return True
        for key in params:
            if any(token == key.lower() or token in key.lower() for token in OBJECT_REFERENCE_TOKENS):
                return True
        return False

    def detect_ownership_risk(self, path: str, params: dict[str, Any]) -> bool:
        candidate = any(token in path.lower() for token in OWNERSHIP_HINTS)
        return bool(candidate and self.detect_object_reference(path, params))

    def detect_sensitive(self, path: str, params: dict[str, Any]) -> bool:
        lower = path.lower()
        return any(token in lower for token in SENSITIVE_PATHS) or "graphql" in lower

    def rank_attack_vector(self, path: str, params: dict[str, Any]) -> str:
        lower = path.lower()
        if self.detect_ownership_risk(path, params):
            return "IDOR"
        if "graphql" in lower:
            return "GraphQL logic"
        if "auth" in lower or "login" in lower or "session" in lower or "token" in lower:
            return "Auth bypass"
        if "export" in lower or "download" in lower or "upload" in lower:
            return "Data exposure"
        if any(token in lower for token in ["admin", "dashboard", "manage"]):
            return "Privilege escalation"
        return "Business logic"

    def normalize_params(self, params: Any) -> dict[str, Any]:
        if isinstance(params, dict):
            return params
        if isinstance(params, str):
            try:
                import ast

                parsed = ast.literal_eval(params)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                logger.warning("Failed to normalize query params via ast.literal_eval", exc_info=True)
        return {}

    def score_endpoint(self, path: str, method: str, params: Any) -> dict[str, Any]:
        params = self.normalize_params(params)
        if self.is_low_value(path):
            return {
                "risk_score": 0,
                "vector": "Low value",
                "ownership_risk": False,
                "reason": "Ruta de bajo valor o contenido estático detectado.",
                "actionable": False,
            }

        method_upper = method.upper()
        us = unified_score(path, method_upper, params)

        ownership = self.detect_ownership_risk(path, params)
        object_ref = self.detect_object_reference(path, params)
        sensitive = self.detect_sensitive(path, params)
        graphql = "graphql" in path.lower()
        api_path = "/api/" in path.lower() or path.lower().startswith("api")

        sc = us["risk_score"]

        reasons: list[str] = []
        if graphql:
            reasons.append("GraphQL expone lógica compleja y potencial cantidad variable de data.")
        if object_ref:
            reasons.append("Referencia de objeto detectada en la URL o parámetros.")
        if ownership:
            reasons.append("Punto de propiedad de recursos con posible control de acceso débil.")
        if sensitive:
            reasons.append("Endpoint sensible o de exportación detectado.")
        if api_path:
            reasons.append("Ruta API expuesta, foco en lógica de aplicación.")
        if method_upper in {"POST", "PUT", "PATCH", "DELETE"}:
            reasons.append("Método HTTP mutador, mayor potencial de impacto.")
        if any(param in params for param in ["user_id", "account_id", "order_id", "file_id", "device_id"]):
            reasons.append("Parámetros de referencia de usuario/objeto presentes.")
        if any(token in path.lower() for token in ["/delete", "/remove", "/transfer", "/approve", "/reject"]):
            reasons.append("Operación sensible de negocio detectada.")

        if "health" in path.lower() or "status" in path.lower():
            sc = 0.0
            reasons = ["Ruta de verificación de estado sin valor de ataque real."]
        vector = us["vector"]
        reasoning = " ".join(reasons) if reasons else "Endpoint sospechoso según patrones de negocio."

        suggestions = unified_suggestions(path, method_upper, params)
        return {
            "risk_score": sc,
            "vector": vector,
            "ownership_risk": ownership,
            "reason": reasoning,
            "suggestions": suggestions,
            "actionable": us["actionable"],
        }

    def evaluate_endpoints(self, endpoints: Iterable[dict[str, Any]]) -> dict[str, Any]:
        entries: list[dict[str, Any]] = []
        by_vector: dict[str, list[dict[str, Any]]] = {}

        for ep in endpoints:
            path = ep.get("path", "")
            method = ep.get("method", "GET")
            params = ep.get("params") or {}
            if isinstance(params, str):
                params = self.normalize_params(params)
            decision = self.score_endpoint(path, method, params)
            if not decision["actionable"]:
                continue
            entry = {
                "path": path,
                "method": method,
                "target_id": ep.get("target_id"),
                "risk_score": decision["risk_score"],
                "vector": decision["vector"],
                "ownership_risk": decision["ownership_risk"],
                "reason": decision["reason"],
                "suggestions": decision["suggestions"],
            }
            entries.append(entry)
            by_vector.setdefault(decision["vector"], []).append(entry)

        entries.sort(key=lambda item: item["risk_score"], reverse=True)
        top = entries[:10]

        ownership = [e for e in top if e["ownership_risk"]]
        attack_vectors = [
            {"vector": vector, "endpoints": [e["path"] for e in items], "count": len(items)}
            for vector, items in by_vector.items()
        ]

        suggested_manual_tests: list[str] = []
        for item in top:
            suggested_manual_tests.extend([
                f"[{item['vector']}] {item['path']} -> {suggestion}" for suggestion in item["suggestions"]
            ])

        vector_summary = ", ".join(sorted({item['vector'] for item in top})) if top else "ninguno"
        summary = (
            f"Evaluación de {len(top)} endpoints accionables. Vectores detectados: {vector_summary}."
            if top
            else "No se encontraron endpoints accionables con el motor actual."
        )

        return {
            "summary": summary,
            "high_value_targets": top,
            "attack_vectors": attack_vectors,
            "ownership_risks": ownership,
            "manual_test_suggestions": suggested_manual_tests[:20],
        }
