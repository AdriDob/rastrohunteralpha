import re
from typing import Any, Dict, List, Optional, Set


UUID_PATTERN = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)

NUMERIC_SEGMENT_PATTERN = re.compile(r"/(?:[0-9]+)(?:/|$)")

STATIC_EXTENSIONS: Set[str] = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg",
    ".woff", ".woff2", ".ttf", ".css", ".js",
    ".map", ".ico", ".mp4", ".webm",
}

LOW_VALUE_PATTERNS: List[str] = [
    "/health", "/status", "/metrics", "/favicon.ico",
    "/robots.txt", "/sitemap.xml", "/ping",
]

AUTH_KEYWORDS: List[str] = [
    "login", "auth", "session", "token", "password",
    "oauth", "signin", "signup", "refresh", "apikey", "jwt",
]

MULTI_TENANT_KEYWORDS: List[str] = [
    "org", "tenant", "workspace", "account", "company", "team", "member",
]

ADMIN_KEYWORDS: List[str] = [
    "admin", "dashboard", "internal", "staff", "superuser", "management",
]

EXPORT_KEYWORDS: List[str] = [
    "export", "download", "backup", "report", "csv", "pdf",
]

UPLOAD_KEYWORDS: List[str] = [
    "upload", "attachment", "file", "import",
]

GRAPHQL_KEYWORDS: List[str] = [
    "graphql", "gql",
]

IDOR_PARAMS: List[str] = [
    "id", "user_id", "org_id", "tenant_id", "account_id",
    "workspace_id", "member_id", "team_id",
]

AUTH_SMELL_TOKENS: List[str] = [
    "org_id", "tenant_id", "workspace_id", "account_id",
    "user_id", "team_id",
]

OBJECT_REFERENCE_TOKENS: List[str] = [
    "user_id", "uid", "account_id", "order_id", "invoice_id",
    "device_id", "file_id", "customer_id", "subscription_id",
    "team_id", "project_id", "resource_id", "session_id",
]

OWNERSHIP_HINTS: List[str] = [
    "user", "account", "profile", "order", "invoice",
    "subscription", "device", "tenant", "org", "project",
    "team", "resource", "member",
]

HIGH_VALUE_KEYWORDS: Set[str] = {
    "billing", "admin", "internal", "graphql", "export",
    "attachments", "uploads", "reports", "audit", "token",
    "apikey", "keys", "invite", "organization", "workspace", "tenant",
}

BILLING_KEYWORDS: List[str] = [
    "billing", "invoice", "subscription", "payment", "transfer",
]

IDENTITY_KEYWORDS: List[str] = [
    "invite", "member", "user",
]

SENSITIVE_OPERATIONS: List[str] = [
    "/delete", "/remove", "/transfer", "/approve", "/reject",
]

WEB3_KEYWORDS: List[str] = [
    "wallet", "balance", "transfer", "tx", "transaction",
    "signature", "nonce", "rpc", "infura", "alchemy",
    "contract", "ethereum", "solana", "web3", "chain",
]

RPC_KEYWORDS: List[str] = [
    "eth_", "net_", "web3_", "sol_", "jsonrpc",
]


class EndpointScorer:
    """
    Unified scoring engine for Rastro.
    Single source of truth for all endpoint and target scoring signals.
    Deterministic, pure, no side effects, no external calls.

    Replaces scoring logic previously scattered across:
      - core/scoring/scorer.py (Scorer.score_endpoint / score_target)
      - core/analysis/analyzer.py (classify_endpoint risk_score)
      - core/recon/parser.py (calculate_score)
      - core/attack/engine.py (score_endpoint)
      - dashboard/app.py (score_endpoint_record)
      - main.py (/digest inline scoring)
    """

    def score_endpoint(
        self,
        path: str,
        method: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        safe_path = str(path or "/")
        safe_method = str(method or "GET").upper()
        safe_params = params or {}

        lower = safe_path.lower()

        if self._is_low_value(lower):
            return {
                "risk_score": 0.0,
                "priority": 0.0,
                "labels": [],
                "signals": ["low_value"],
                "attack_surface": [],
                "is_auth_related": False,
                "is_admin": False,
                "is_graphql": False,
                "potential_idor": False,
            }

        if any(lower.endswith(ext) for ext in STATIC_EXTENSIONS):
            return {
                "risk_score": 0.0,
                "priority": 0.0,
                "labels": [],
                "signals": ["static_asset"],
                "attack_surface": [],
                "is_auth_related": False,
                "is_admin": False,
                "is_graphql": False,
                "potential_idor": False,
            }

        labels: List[str] = []
        signals: List[str] = []
        attack_surface: List[str] = []
        score: float = 0.0

        is_api = (
            "/api/" in lower
            or lower.startswith("api")
            or "/v1/" in lower
            or "/v2/" in lower
        )
        if is_api:
            labels.append("api")
        else:
            labels.append("web")

        if any(kw in lower for kw in GRAPHQL_KEYWORDS):
            labels.append("graphql")
            attack_surface.append("graphql_attack_surface")
            score += 25.0
            signals.append("graphql")

        if any(kw in lower for kw in ADMIN_KEYWORDS):
            labels.append("admin")
            labels.append("sensitive")
            attack_surface.append("admin_surface")
            score += 25.0
            signals.append("admin")

        if any(kw in lower for kw in EXPORT_KEYWORDS):
            labels.append("export")
            labels.append("sensitive")
            attack_surface.append("data_exfiltration")
            score += 35.0
            signals.append("export")

        if any(kw in lower for kw in UPLOAD_KEYWORDS):
            labels.append("file_operation")
            attack_surface.append("upload_surface")
            score += 18.0
            signals.append("file_operation")

        if any(kw in lower for kw in AUTH_KEYWORDS):
            labels.append("auth")
            attack_surface.append("authentication_surface")
            score += 20.0
            signals.append("auth")

        if any(kw in lower for kw in MULTI_TENANT_KEYWORDS):
            labels.append("multi_tenant")
            attack_surface.append("tenant_boundary")
            score += 30.0
            signals.append("multi_tenant")

        if any(kw in lower for kw in BILLING_KEYWORDS):
            labels.append("billing")
            score += 20.0
            signals.append("billing")

        if any(kw in lower for kw in IDENTITY_KEYWORDS):
            labels.append("identity")
            score += 20.0
            signals.append("identity")

        if "internal" in lower:
            labels.append("internal")
            attack_surface.append("internal_surface")
            score += 20.0
            signals.append("internal")

        if is_api:
            score += 10.0
            signals.append("api_path")

        if "/import" in lower:
            labels.append("import")
            score += 20.0
            signals.append("import")

        has_uuid = bool(UUID_PATTERN.search(safe_path))
        has_numeric = bool(NUMERIC_SEGMENT_PATTERN.search(safe_path))

        if has_uuid:
            labels.append("uuid_identifier")
            score += 25.0
            signals.append("uuid")

        if has_numeric:
            labels.append("numeric_identifier")
            score += 18.0
            signals.append("numeric_id")

        web3_keywords_hit = [kw for kw in WEB3_KEYWORDS if kw in lower]
        rpc_keywords_hit = [kw for kw in RPC_KEYWORDS if kw in lower]
        if web3_keywords_hit or rpc_keywords_hit:
            labels.append("web3")
            score += 20.0
            signals.append("web3")
            if rpc_keywords_hit:
                attack_surface.append("rpc_surface")
                score += 10.0
            if "wallet" in lower or "balance" in lower:
                attack_surface.append("wallet_surface")
                score += 15.0
            if "signature" in lower or "nonce" in lower:
                attack_surface.append("signature_surface")
                score += 12.0

        if safe_method in {"PUT", "PATCH", "DELETE"}:
            labels.append("mutation")
            score += 15.0
            signals.append("mutating_method")
        elif safe_method == "POST":
            score += 10.0
            signals.append("post_method")

        auth_smells: List[str] = []

        if safe_params:
            lowered_params = [str(p).lower() for p in safe_params.keys()]

            if any(p in IDOR_PARAMS for p in lowered_params):
                labels.append("id_parameter")
                attack_surface.append("idor_candidate")
                score += 22.0
                signals.append("idor_params")

            if any(
                any(token == p or token in p for token in OBJECT_REFERENCE_TOKENS)
                for p in lowered_params
            ):
                score += 10.0
                signals.append("object_reference_param")

            for param in lowered_params:
                if any(smell in param for smell in MULTI_TENANT_KEYWORDS):
                    auth_smells.append(param)

        for token in AUTH_SMELL_TOKENS:
            if token in lower:
                auth_smells.append(token)

        if auth_smells:
            score += 28.0
            signals.append("auth_smell")

        has_ownership_hint = any(token in lower for token in OWNERSHIP_HINTS)
        has_object_ref = any(token in lower for token in OBJECT_REFERENCE_TOKENS)

        if has_ownership_hint and (has_object_ref or has_uuid or has_numeric):
            score += 18.0
            signals.append("ownership_risk")
            attack_surface.append("ownership_boundary")

        if any(op in lower for op in SENSITIVE_OPERATIONS):
            score += 8.0
            signals.append("sensitive_operation")

        if any(kw in lower for kw in HIGH_VALUE_KEYWORDS):
            score += 10.0
            signals.append("high_value_keyword")

        risk_score = round(min(score, 100.0), 1)

        return {
            "risk_score": risk_score,
            "priority": risk_score,
            "labels": sorted(set(labels)),
            "signals": sorted(set(signals)),
            "attack_surface": sorted(set(attack_surface)),
            "is_auth_related": "auth" in labels,
            "is_admin": "admin" in labels,
            "is_graphql": "graphql" in labels,
            "potential_idor": (
                "id_parameter" in labels
                or "idor_candidate" in attack_surface
                or "ownership_boundary" in attack_surface
                or bool(auth_smells)
                or has_object_ref
            ),
        }

    def score_target(self, meta: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        meta = meta or {}
        score = 0.0

        if meta.get("is_saas"):
            score += 20.0
        if meta.get("has_api"):
            score += 25.0
        if meta.get("multi_tenant"):
            score += 30.0
        if meta.get("has_admin"):
            score += 20.0
        if meta.get("has_graphql"):
            score += 15.0
        if meta.get("enterprise"):
            score += 15.0
        if meta.get("internal_api"):
            score += 15.0

        quality = min(score, 100.0)

        return {
            "priority": quality,
            "saaS_probability": 85.0 if meta.get("is_saas") else 35.0,
            "target_quality": quality,
        }

    @staticmethod
    def _is_low_value(lower_path: str) -> bool:
        for pattern in LOW_VALUE_PATTERNS:
            if pattern in lower_path:
                return True
        return False
