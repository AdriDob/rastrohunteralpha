import re
from collections.abc import Iterable
from typing import Any

from core_engines.engine.unified_scoring import score

UUID_PATTERN = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)

NUMERIC_PATTERN = re.compile(r"/(?:[0-9]+)(?:/|$)")

AUTH_SMELL_TOKENS = [
    "org_id", "tenant_id", "workspace_id",
    "account_id", "user_id", "team_id",
]

ADMIN_KEYWORDS = [
    "admin", "dashboard", "internal", "staff", "superuser", "management",
]

GRAPHQL_KEYWORDS = ["graphql", "gql"]

MULTI_TENANT_KEYWORDS = [
    "org", "tenant", "workspace", "account", "company", "team", "member",
]

AUTH_KEYWORDS = [
    "login", "auth", "session", "token", "password",
    "oauth", "signin", "signup", "refresh", "apikey", "jwt",
]

EXPORT_KEYWORDS = [
    "export", "download", "backup", "report", "csv", "pdf",
]

UPLOAD_KEYWORDS = [
    "upload", "attachment", "file", "import",
]

IDOR_PARAMS = [
    "id", "user_id", "org_id", "tenant_id", "account_id",
    "workspace_id", "member_id", "team_id",
]


def classify(
    path: str,
    method: str = "GET",
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Unified endpoint classification.

    Replaces:
      - EndpointAnalyzer.classify_endpoint
      - EndpointParser.detect_labels / detect_auth_smells
      - dashboard/app.py inline classification heuristics
    """
    safe_path = str(path or "/")
    safe_method = str(method or "GET").upper()
    safe_params = params or {}
    lower = safe_path.lower()

    labels: list[str] = []
    auth_smells: list[str] = []
    attack_surface: list[str] = []

    is_api = (
        "/api/" in lower
        or lower.startswith("api")
        or lower.endswith("graphql")
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

    if any(kw in lower for kw in ADMIN_KEYWORDS):
        labels.append("admin")
        labels.append("sensitive")
        attack_surface.append("admin_surface")

    if any(kw in lower for kw in EXPORT_KEYWORDS):
        labels.append("export")
        labels.append("sensitive")
        attack_surface.append("data_exfiltration")

    if any(kw in lower for kw in UPLOAD_KEYWORDS):
        labels.append("file_operation")
        attack_surface.append("upload_surface")

    if any(kw in lower for kw in AUTH_KEYWORDS):
        labels.append("auth")
        attack_surface.append("authentication_surface")

    if any(kw in lower for kw in MULTI_TENANT_KEYWORDS):
        labels.append("multi_tenant")
        attack_surface.append("tenant_boundary")

    if safe_method in {"PUT", "PATCH", "DELETE"}:
        labels.append("mutation")

    if safe_params:
        lowered_params = [str(p).lower() for p in safe_params]

        if any(param in IDOR_PARAMS for param in lowered_params):
            labels.append("id_parameter")
            attack_surface.append("idor_candidate")

        for param in lowered_params:
            if any(smell in param for smell in MULTI_TENANT_KEYWORDS):
                auth_smells.append(param)

    for smell in IDOR_PARAMS:
        if smell in lower:
            auth_smells.append(smell)

    if any(part.isdigit() for part in lower.split("/")):
        labels.append("numeric_identifier")

    if any(
        len(part) >= 24 and "-" in part
        for part in lower.split("/")
    ):
        labels.append("uuid_identifier")

    sc = score(safe_path, safe_method, safe_params)

    return {
        "path": safe_path,
        "method": safe_method,
        "labels": sorted(set(labels)),
        "auth_smells": sorted(set(auth_smells)),
        "attack_surface": sorted(set(attack_surface)),
        "risk_score": sc["risk_score"],
        "confidence": sc["confidence"],
        "vector": sc["vector"],
        "signals": sc["signals"],
        "is_graphql": "graphql" in labels,
        "is_admin": "admin" in labels,
        "is_multi_tenant": "multi_tenant" in labels,
        "is_auth_related": "auth" in labels,
        "potential_idor": sc["potential_idor"],
        "actionable": sc["actionable"],
    }


def synthesize_target_meta(
    endpoints: Iterable[dict[str, Any]],
) -> dict[str, bool]:
    """
    Unified target-level metadata synthesis.

    Replaces EndpointAnalyzer.synthesize_target_meta.
    """
    has_api = False
    has_graphql = False
    has_admin = False
    multi_tenant = False
    auth_heavy = False
    has_uploads = False
    has_exports = False
    has_bola_surface = False

    for endpoint in endpoints:
        path = str(endpoint.get("path", "")).lower()
        labels = endpoint.get("labels", [])
        if isinstance(labels, str):
            labels = [labels]

        if "/api/" in path or path.startswith("api"):
            has_api = True

        if "graphql" in path or "graphql" in labels:
            has_graphql = True

        if any(kw in path for kw in ADMIN_KEYWORDS):
            has_admin = True

        if any(kw in path for kw in MULTI_TENANT_KEYWORDS):
            multi_tenant = True
            has_bola_surface = True

        if any(kw in path for kw in AUTH_KEYWORDS):
            auth_heavy = True

        if any(kw in path for kw in UPLOAD_KEYWORDS):
            has_uploads = True

        if any(kw in path for kw in EXPORT_KEYWORDS):
            has_exports = True

    return {
        "has_api": has_api,
        "has_graphql": has_graphql,
        "has_admin": has_admin,
        "multi_tenant": multi_tenant,
        "auth_heavy": auth_heavy,
        "has_uploads": has_uploads,
        "has_exports": has_exports,
        "has_bola_surface": has_bola_surface,
    }
