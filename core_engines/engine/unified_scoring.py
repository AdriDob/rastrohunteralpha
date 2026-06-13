import re
from functools import lru_cache
from typing import Any, Dict, List, Optional, Set, Tuple


UUID_PATTERN = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)

NUMERIC_SEGMENT_PATTERN = re.compile(r"/(?:[0-9]+)(?:/|$)")
ID_PATTERN = re.compile(r"(?:user|account|order|invoice|device|file|customer|subscription|team|project|resource)_?id", re.I)
NOUN_ID_PATTERN = re.compile(r"/(?:[A-Za-z]+)-?(?:id|uuid|key|token)(?:/|$)", re.I)

STATIC_EXTENSIONS: Set[str] = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg",
    ".woff", ".woff2", ".ttf", ".css", ".js",
    ".map", ".ico", ".mp4", ".webm",
}

LOW_VALUE_PATTERNS: List[str] = [
    "/health", "/status", "/metrics", "/favicon.ico",
    "/robots.txt", "/sitemap.xml", "/ping", "/version",
    "/swagger-resources", "/v2/api-docs", "/webjars",
    "/actuator", "/heartbeat", "/ready", "/live",
    "/static/", "/assets/", "/css/", "/js/", "/images/",
    "/logo",
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

SENSITIVE_PATHS: List[str] = [
    "admin", "dashboard", "export", "download",
    "settings", "profile", "billing", "payment",
    "transfer", "report",
]

LOW_VALUE_ATTACK_PATTERNS: List[str] = [
    r"/health", r"/status", r"/metrics", r"/favicon\.ico",
    r"/robots\.txt", r"/sitemap\.xml", r"/static/",
    r"/assets/", r"/css/", r"/js/", r"/images/",
    r"/logo", r"/ping",
]

ATTACK_VECTOR_KEYWORDS: Dict[str, List[str]] = {
    "IDOR": ["user_id", "account_id", "order_id", "file_id", "device_id",
             "customer_id", "subscription_id", "team_id", "project_id",
             "resource_id", "uid"],
    "Auth bypass": ["auth", "login", "session", "token"],
    "Data exposure": ["export", "download", "upload"],
    "Privilege escalation": ["admin", "dashboard", "manage"],
    "GraphQL logic": ["graphql", "gql"],
}


def _is_low_value_path(lower_path: str) -> bool:
    for pattern in LOW_VALUE_PATTERNS:
        if pattern in lower_path:
            return True
    return False


def _is_static_asset(lower_path: str) -> bool:
    return any(lower_path.endswith(ext) for ext in STATIC_EXTENSIONS)


def _rank_attack_vector(path: str, params: Optional[Dict[str, Any]]) -> str:
    lower = path.lower()
    p = params or {}

    has_ownership = bool(
        any(token in lower for token in OWNERSHIP_HINTS)
        and (
            any(token in lower for token in OBJECT_REFERENCE_TOKENS)
            or bool(UUID_PATTERN.search(path))
            or bool(NUMERIC_SEGMENT_PATTERN.search(path))
            or any(
                any(ref == k.lower() for ref in OBJECT_REFERENCE_TOKENS)
                for k in p.keys()
            )
        )
    )
    if has_ownership:
        return "IDOR"

    for vector, keywords in ATTACK_VECTOR_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return vector

    return "Business logic"


_score_cache: Dict[Tuple[str, str, str], Dict[str, Any]] = {}

try:
    from core_engines.config import get_config
    _MAX_CACHE = get_config().cache_size
except Exception:
    _MAX_CACHE = 4096


def _make_score_key(path: str, method: str, params: Optional[Dict[str, Any]]) -> Tuple[str, str, str]:
    params_key = str(sorted((params or {}).items()))
    return (path, method.upper(), params_key)


def score(
    path: str,
    method: str = "GET",
    params: Optional[Dict[str, Any]] = None,
    target_meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Unified scoring engine — single source of truth for Rastro.

    Fuses all prior scoring logic:
      - EndpointScorer.score_endpoint / score_target
      - Scorer.score_endpoint / score_target
      - AttackDecisionEngine.score_endpoint
      - EndpointAnalyzer.classify_endpoint risk_score
      - EndpointParser scoring
      - dashboard/app.py score_endpoint_record
      - main.py /digest inline scoring
      - core/targets/scorer.py score_target

    Returns a normalized dict with risk_score, vector, confidence, signals.
    """
    key = _make_score_key(path, method, params)
    cached = _score_cache.get(key)
    if cached is not None:
        return cached
    safe_path = str(path or "/")
    safe_method = str(method or "GET").upper()
    safe_params = params or {}
    lower = safe_path.lower()

    is_low_value = _is_low_value_path(lower)
    is_static = _is_static_asset(lower)

    if is_low_value or is_static:
        vector = "Low value" if is_low_value else "Static asset"
        return {
            "risk_score": 0.0,
            "vector": vector,
            "confidence": 0.0,
            "signals": [vector.lower().replace(" ", "_")],
            "labels": [],
            "attack_surface": [],
            "auth_smells": [],
            "potential_idor": False,
            "actionable": False,
            "is_auth_related": False,
            "is_admin": False,
            "is_graphql": False,
        }

    labels: List[str] = []
    signals: List[str] = []
    attack_surface: List[str] = []
    auth_smells: List[str] = []
    score_val: float = 0.0

    is_api = (
        "/api/" in lower
        or lower.startswith("api")
        or "/v1/" in lower
        or "/v2/" in lower
    )
    if is_api:
        labels.append("api")
        score_val += 10.0
        signals.append("api_path")
    else:
        labels.append("web")

    if any(kw in lower for kw in GRAPHQL_KEYWORDS):
        labels.append("graphql")
        attack_surface.append("graphql_attack_surface")
        score_val += 25.0
        signals.append("graphql")

    if any(kw in lower for kw in ADMIN_KEYWORDS):
        labels.append("admin")
        labels.append("sensitive")
        attack_surface.append("admin_surface")
        score_val += 25.0
        signals.append("admin")

    if any(kw in lower for kw in EXPORT_KEYWORDS):
        labels.append("export")
        labels.append("sensitive")
        attack_surface.append("data_exfiltration")
        score_val += 35.0
        signals.append("export")

    if any(kw in lower for kw in UPLOAD_KEYWORDS):
        labels.append("file_operation")
        attack_surface.append("upload_surface")
        score_val += 18.0
        signals.append("file_operation")

    if any(kw in lower for kw in AUTH_KEYWORDS):
        labels.append("auth")
        attack_surface.append("authentication_surface")
        score_val += 20.0
        signals.append("auth")

    if any(kw in lower for kw in MULTI_TENANT_KEYWORDS):
        labels.append("multi_tenant")
        attack_surface.append("tenant_boundary")
        score_val += 30.0
        signals.append("multi_tenant")

    if any(kw in lower for kw in BILLING_KEYWORDS):
        labels.append("billing")
        score_val += 20.0
        signals.append("billing")

    if any(kw in lower for kw in IDENTITY_KEYWORDS):
        labels.append("identity")
        score_val += 20.0
        signals.append("identity")

    if "internal" in lower:
        labels.append("internal")
        attack_surface.append("internal_surface")
        score_val += 20.0
        signals.append("internal")

    if "/import" in lower:
        labels.append("import")
        score_val += 20.0
        signals.append("import")

    has_uuid = bool(UUID_PATTERN.search(safe_path))
    has_numeric = bool(NUMERIC_SEGMENT_PATTERN.search(safe_path))

    if has_uuid:
        labels.append("uuid_identifier")
        score_val += 25.0
        signals.append("uuid")

    if has_numeric:
        labels.append("numeric_identifier")
        score_val += 18.0
        signals.append("numeric_id")

    web3_keywords_hit = [kw for kw in WEB3_KEYWORDS if kw in lower]
    rpc_keywords_hit = [kw for kw in RPC_KEYWORDS if kw in lower]
    if web3_keywords_hit or rpc_keywords_hit:
        labels.append("web3")
        score_val += 20.0
        signals.append("web3")
        if rpc_keywords_hit:
            attack_surface.append("rpc_surface")
            score_val += 10.0
        if "wallet" in lower or "balance" in lower:
            attack_surface.append("wallet_surface")
            score_val += 15.0
        if "signature" in lower or "nonce" in lower:
            attack_surface.append("signature_surface")
            score_val += 12.0

    if safe_method in {"PUT", "PATCH", "DELETE"}:
        labels.append("mutation")
        score_val += 15.0
        signals.append("mutating_method")
    elif safe_method == "POST":
        score_val += 10.0
        signals.append("post_method")

    if safe_params:
        lowered_params = [str(p).lower() for p in safe_params.keys()]

        if any(p in IDOR_PARAMS for p in lowered_params):
            labels.append("id_parameter")
            attack_surface.append("idor_candidate")
            score_val += 22.0
            signals.append("idor_params")

        if any(
            any(token == p or token in p for token in OBJECT_REFERENCE_TOKENS)
            for p in lowered_params
        ):
            score_val += 10.0
            signals.append("object_reference_param")

        for param in lowered_params:
            if any(smell in param for smell in MULTI_TENANT_KEYWORDS):
                auth_smells.append(param)

    for token in AUTH_SMELL_TOKENS:
        if token in lower:
            auth_smells.append(token)

    if auth_smells:
        score_val += 28.0
        signals.append("auth_smell")

    has_ownership_hint = any(token in lower for token in OWNERSHIP_HINTS)
    has_object_ref = any(token in lower for token in OBJECT_REFERENCE_TOKENS)

    if has_ownership_hint and (has_object_ref or has_uuid or has_numeric):
        score_val += 18.0
        signals.append("ownership_risk")
        attack_surface.append("ownership_boundary")

    if any(op in lower for op in SENSITIVE_OPERATIONS):
        score_val += 8.0
        signals.append("sensitive_operation")

    if any(kw in lower for kw in HIGH_VALUE_KEYWORDS):
        score_val += 10.0
        signals.append("high_value_keyword")

    risk_score = round(min(score_val, 100.0), 1)
    vector = _rank_attack_vector(safe_path, safe_params)
    potential_idor = (
        "id_parameter" in labels
        or "idor_candidate" in attack_surface
        or "ownership_boundary" in attack_surface
        or bool(auth_smells)
        or has_object_ref
    )

    confidence = round(min(risk_score / 100.0, 1.0), 2)

    result = {
        "risk_score": risk_score,
        "vector": vector,
        "confidence": confidence,
        "signals": sorted(set(signals)),
        "labels": sorted(set(labels)),
        "attack_surface": sorted(set(attack_surface)),
        "auth_smells": sorted(set(auth_smells)),
        "potential_idor": potential_idor,
        "actionable": risk_score >= 25.0,
        "is_auth_related": "auth" in labels,
        "is_admin": "admin" in labels,
        "is_graphql": "graphql" in labels,
    }
    if len(_score_cache) < _MAX_CACHE:
        _score_cache[key] = result
    return result


def score_target(meta: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
    """
    Unified target-level scoring.

    Fuses:
      - EndpointScorer.score_target
      - Scorer.score_target
      - core/targets/scorer.py score_target
    """
    meta = meta or {}
    score_val = 0.0
    complexity = 0.0
    roi = 0.0

    has_graphql = meta.get("has_graphql") or meta.get("graphql", False)
    if has_graphql:
        score_val += 20.0
        complexity += 10.0
        roi += 15.0

    api_count = int(meta.get("api_count") or 0)
    if api_count:
        score_val += min(api_count * 6, 30)
        complexity += min(api_count * 4, 30)
        roi += min(api_count * 5, 30)
    elif meta.get("has_api"):
        score_val += 25.0
        roi += 10.0

    is_saas = meta.get("is_saas", False)
    saas_prob = float(meta.get("saas_prob") or 0.0)
    if is_saas or saas_prob > 0.5:
        score_val += 25.0
        complexity += 10.0
        roi += 20.0

    if meta.get("multi_tenant"):
        score_val += 30.0
        complexity += 20.0
        roi += 20.0

    if meta.get("has_admin") or meta.get("admin"):
        score_val += 20.0
        complexity += 10.0
        roi += 10.0

    if meta.get("enterprise") or meta.get("b2b"):
        score_val += 15.0
        roi += 10.0

    if meta.get("internal_api"):
        score_val += 15.0

    if meta.get("has_exports") or meta.get("export"):
        score_val += 10.0
        roi += 8.0

    if meta.get("auth_heavy"):
        complexity += 15.0
        roi += 10.0

    if meta.get("static"):
        score_val -= 30.0

    quality = min(max(score_val, 0.0), 100.0)
    complexity_score = min(complexity, 100.0)
    roi_score = min(roi, 100.0)

    source = str(meta.get("source", "")).lower()
    competition = 50.0
    if source in ("hackerone", "bugcrowd"):
        competition = 85.0
    elif source == "intigriti":
        competition = 60.0
    elif source == "yeswehack":
        competition = 40.0
    elif source:
        competition = 30.0

    freshness = float(meta.get("freshness", 75.0))
    attack_surface_score = min(
        (api_count * 10) + (30 if meta.get("wildcard") else 0)
        + (10 if has_graphql else 0),
        100.0,
    )
    opportunity_score = min(
        max(
            50.0 + (freshness * 0.5) - (competition * 0.8)
            + (attack_surface_score * 0.6) + (roi_score * 0.2),
            0.0,
        ),
        100.0,
    )

    return {
        "priority": quality,
        "quality": quality,
        "complexity_score": complexity_score,
        "roi_score": roi_score,
        "opportunity_score": opportunity_score,
        "competition_score": competition,
        "freshness_score": freshness,
        "attack_surface_score": attack_surface_score,
        "saaS_probability": 85.0 if is_saas else 35.0,
        "target_quality": quality,
    }


def generate_suggestions(path: str, method: str, params: Dict[str, Any]) -> List[str]:
    suggestions: List[str] = []
    lower = path.lower()
    p = params or {}

    has_ownership = bool(
        any(token in lower for token in OWNERSHIP_HINTS)
        and (
            any(token in lower for token in OBJECT_REFERENCE_TOKENS)
            or bool(UUID_PATTERN.search(path))
            or bool(NUMERIC_SEGMENT_PATTERN.search(path))
            or any(
                any(ref == k.lower() for ref in OBJECT_REFERENCE_TOKENS)
                for k in p.keys()
            )
        )
    )

    if has_ownership:
        suggestions.append(
            "Modificar el identificador de recurso (user_id/order_id/file_id) "
            "y reproducir con otra cuenta de sesión."
        )
        suggestions.append(
            "Intentar acceso cruzado entre cuentas para detectar "
            "debilidad en límites de propiedad."
        )
    if "graphql" in lower:
        suggestions.append(
            "Enviar consultas GraphQL con parámetros de usuario/objeto "
            "alternados para detectar filtrado débil."
        )
    if method in {"POST", "PUT", "PATCH", "DELETE"}:
        suggestions.append(
            "Probar manipulación de parámetros en solicitudes mutadoras "
            "para escalar privilegios o alterar asociaciones."
        )
    if any(token in lower for token in ["export", "download"]):
        suggestions.append(
            "Solicitar recursos con IDs de otros usuarios para probar "
            "exposición de datos."
        )
    if any(token in lower for token in ["auth", "login", "token", "session"]):
        suggestions.append(
            "Intentar bypass de autorización usando tokens inválidos "
            "o IDs de usuario distintos."
        )
    if not suggestions:
        suggestions.append(
            "Revisar esta ruta por lógica de negocio relevante y posibles "
            "controles de autorización débiles."
        )
    return suggestions
