"""
hypothesis.generators — Deterministic rule-based hypothesis generation.

Each generator inspects scored/classified endpoint data and produces
concrete vulnerability hypotheses with supporting evidence.
"""

from __future__ import annotations

import re
import hashlib
from typing import Any, Dict, List, Optional, Set

from core_engines.engine.hypothesis.models import (
    Hypothesis,
    HypothesisSource,
    VulnerabilityType,
)

UUID_PATTERN = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
NUMERIC_SEGMENT = re.compile(r"/(?:[0-9]+)(?:/|$)")
ID_PARAM = re.compile(r"(?:user|account|order|invoice|file|team|org|project|resource|customer|subscription|device)_?id", re.I)
UUID_PARAM = re.compile(r"(?:uuid|token|session|key|guid|ref)_?", re.I)


def _hyp_id(vt: str, ep_id: int, suffix: str = "") -> str:
    raw = f"{vt}:{ep_id}:{suffix}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def generate_idor(
    ep: Dict[str, Any], target_id: int, target_name: str,
) -> Optional[Hypothesis]:
    path: str = str(ep.get("path", ""))
    method: str = str(ep.get("method", "GET")).upper()
    signals: List[str] = ep.get("signals", [])
    labels: List[str] = ep.get("labels", [])
    surface: List[str] = ep.get("attack_surface", [])
    risk_score: float = float(ep.get("risk_score", 0))
    potential_idor: bool = ep.get("potential_idor", False)

    has_idor_signal = (
        potential_idor
        or any(s in surface for s in {"ownership_boundary", "tenant_boundary"})
        or any(s in signals for s in {
            "uuid", "numeric_id", "idor_params", "ownership_risk",
            "object_reference_param", "auth_smell",
        })
        or "id_parameter" in labels
    )
    if not has_idor_signal or risk_score < 20:
        return None

    if UUID_PATTERN.search(path):
        identifier = "UUID"
    elif NUMERIC_SEGMENT.search(path):
        identifier = "numeric_id"
    else:
        identifier = "object_reference"

    has_ownership = any(s in signals for s in {"ownership_risk", "auth_smell"})
    has_multi_tenant = any(s in surface for s in {"tenant_boundary"}) or "multi_tenant" in labels
    is_mutating = method in ("POST", "PUT", "PATCH", "DELETE")
    is_read = method in ("GET",)

    evidence = []
    if identifier == "UUID":
        evidence.append("Path contains UUID identifier — replaceable object reference")
    elif identifier == "numeric_id":
        evidence.append("Path contains numeric ID — enumerable object reference")
    if has_ownership:
        evidence.append("Ownership/auth smell detected — cross-user access may be possible")
    if has_multi_tenant:
        evidence.append("Multi-tenant endpoint — tenant boundary may be violable")
    if is_mutating:
        evidence.append(f"Mutating method ({method}) — unauthorized modification risk")
    if "uuid" in signals:
        evidence.append("UUID signal — deterministic object reference")
    if "idor_params" in signals:
        evidence.append("IDOR parameters detected in request pattern")
    evidence.append(f"risk_score={risk_score:.0f} | surface={', '.join(surface) if surface else 'none'}")

    actions = []
    if identifier == "UUID":
        actions.append(f"Replace UUID in path with a different user's UUID and verify access")
    elif identifier == "numeric_id":
        actions.append(f"Increment/decrement numeric ID in path and verify unauthorized access")
    if has_multi_tenant and is_read:
        actions.append("Attempt to access resources from another tenant by modifying tenant-scoped identifiers")
    if is_mutating:
        actions.append(f"Send {method} with modified object ID and verify authorization enforcement")

    ep_id = int(ep.get("id", 0))
    return Hypothesis(
        id=_hyp_id("idor", ep_id),
        vulnerability_type=VulnerabilityType.IDOR,
        target_id=target_id,
        target_name=target_name,
        endpoint=ep,
        likelihood=min(risk_score / 100.0 + (0.15 if has_ownership else 0), 0.95),
        impact=0.85 if is_mutating else 0.65,
        exploitability=0.75 if identifier == "numeric_id" else 0.55,
        confidence=0.0,
        priority_score=0.0,
        evidence=evidence,
        reasoning=f"Endpoint has {identifier} in path with IDOR signals — replace reference to test for broken object-level authorization.",
        suggested_actions=actions,
        source=HypothesisSource.RULE,
        vector="IDOR",
        attack_surface_labels=surface,
    )


def generate_auth_bypass(
    ep: Dict[str, Any], target_id: int, target_name: str,
) -> Optional[Hypothesis]:
    path: str = str(ep.get("path", ""))
    method: str = str(ep.get("method", "GET")).upper()
    signals: List[str] = ep.get("signals", [])
    labels: List[str] = ep.get("labels", [])
    surface: List[str] = ep.get("attack_surface", [])
    risk_score: float = float(ep.get("risk_score", 0))
    lower = path.lower()

    has_auth_signal = (
        "authentication_surface" in surface
        or any(s in signals for s in {"auth", "session", "token", "jwt"})
        or any(kw in lower for kw in {"login", "signin", "oauth", "callback", "reset", "forgot", "sso"})
        or "auth" in labels
    )
    if not has_auth_signal:
        return None

    is_admin = "admin_surface" in surface or "admin" in labels
    is_registration = any(kw in lower for kw in {"signup", "register", "invite"})
    has_token = "token" in signals or "jwt" in signals or any(kw in lower for kw in {"jwt", "token"})

    evidence = []
    if is_admin:
        evidence.append("Admin-facing auth endpoint — privilege escalation via auth bypass")
    if is_registration:
        evidence.append("Registration endpoint — possible self-signup to privileged role")
    if has_token:
        evidence.append("Token/JWT involvement — check for alg=none, missing verification, weak secret")
    evidence.append(f"Auth surface: authentication_surface present | risk_score={risk_score:.0f}")

    actions = []
    if has_token:
        actions.append("Decode JWT token and test 'alg': 'none' attack")
        actions.append("Modify JWT payload claims and re-encode with empty signature")
        actions.append("Test for JWK header injection")
    if is_registration:
        actions.append("Attempt to register with admin/owner role parameter")
    if is_admin:
        actions.append("Test direct admin endpoint access without proper session")
    actions.append("Check for missing/invalid CSRF tokens on mutating auth endpoints")

    ep_id = int(ep.get("id", 0))
    return Hypothesis(
        id=_hyp_id("auth_bypass", ep_id),
        vulnerability_type=VulnerabilityType.AUTH_BYPASS,
        target_id=target_id,
        target_name=target_name,
        endpoint=ep,
        likelihood=0.45 if has_token else 0.35,
        impact=0.95 if is_admin else 0.75,
        exploitability=0.5 if has_token else 0.4,
        confidence=0.0,
        priority_score=0.0,
        evidence=evidence,
        reasoning=f"Auth-related endpoint ({'admin' if is_admin else path}) — test authentication enforcement and token handling.",
        suggested_actions=actions,
        source=HypothesisSource.RULE,
        vector="Auth bypass" if not has_token else "JWT",
        attack_surface_labels=surface,
    )


def generate_ssrf(
    ep: Dict[str, Any], target_id: int, target_name: str,
) -> Optional[Hypothesis]:
    path: str = str(ep.get("path", ""))
    method: str = str(ep.get("method", "GET")).upper()
    signals: List[str] = ep.get("signals", [])
    labels: List[str] = ep.get("labels", [])
    risk_score: float = float(ep.get("risk_score", 0))
    lower = path.lower()

    has_ssrf_signal = (
        any(kw in lower for kw in {"webhook", "callback", "proxy", "fetch", "url", "redirect", "forward", "image", "avatar", "import", "upload", "download"})
        or "file_operation" in labels
        or "upload_surface" in ep.get("attack_surface", [])
        or any(s in signals for s in {"file_operation", "export"})
    )
    if not has_ssrf_signal or risk_score < 10:
        return None

    is_upload = "upload_surface" in ep.get("attack_surface", []) or method == "POST"
    is_webhook = "webhook" in lower
    is_proxy = any(kw in lower for kw in {"proxy", "fetch", "redirect"})

    evidence = []
    if is_upload:
        evidence.append("File upload endpoint — SSRF via file URL or SVG with external entity")
    if is_webhook:
        evidence.append("Webhook endpoint — server makes HTTP request to user-supplied URL")
    if is_proxy:
        evidence.append("Proxy/redirect endpoint — server fetches user-supplied URL")
    evidence.append(f"risk_score={risk_score:.0f} | method={method}")

    actions = []
    if is_upload:
        actions.append("Upload SVG with external entity DTD reference pointing to internal host")
        actions.append("Submit file URL parameter pointing to 127.0.0.1:internal_port")
    if is_webhook or is_proxy:
        actions.append("Supply URL pointing to internal service (http://127.0.0.1:8080)")
        actions.append("Test cloud metadata endpoints (http://169.254.169.254/latest/meta-data/)")
        actions.append("Try DNS rebinding attack with custom domain")
    actions.append("Test with file:///etc/passwd URL scheme")

    ep_id = int(ep.get("id", 0))
    return Hypothesis(
        id=_hyp_id("ssrf", ep_id),
        vulnerability_type=VulnerabilityType.SSRF,
        target_id=target_id,
        target_name=target_name,
        endpoint=ep,
        likelihood=0.4 if is_webhook else 0.3,
        impact=0.85,
        exploitability=0.5,
        confidence=0.0,
        priority_score=0.0,
        evidence=evidence,
        reasoning=f"Endpoint accepts URLs or file inputs — test for server-side request forgery to internal resources.",
        suggested_actions=actions,
        source=HypothesisSource.RULE,
        vector="SSRF",
        attack_surface_labels=ep.get("attack_surface", []),
    )


def generate_privilege_escalation(
    ep: Dict[str, Any], target_id: int, target_name: str,
) -> Optional[Hypothesis]:
    path: str = str(ep.get("path", ""))
    method: str = str(ep.get("method", "GET")).upper()
    signals: List[str] = ep.get("signals", [])
    labels: List[str] = ep.get("labels", [])
    surface: List[str] = ep.get("attack_surface", [])
    risk_score: float = float(ep.get("risk_score", 0))
    lower = path.lower()

    is_admin = "admin_surface" in surface or "admin" in labels
    is_internal = "internal_surface" in surface or "internal" in labels
    has_admin_signal = is_admin or is_internal or any(s in signals for s in {"admin", "internal"})
    has_role_signal = any(kw in lower for kw in {"role", "permission", "admin", "sudo", "superuser", "privilege", "staff", "dashboard"})

    if not (has_admin_signal or has_role_signal):
        return None

    evidence = []
    if is_admin:
        evidence.append("Admin-labeled endpoint — verify role-based access control")
    if is_internal:
        evidence.append("Internal-labeled endpoint — verify network-level access restriction")
    if has_role_signal:
        evidence.append("Role/permission parameter in path — test for vertical privilege escalation")
    evidence.append(f"risk_score={risk_score:.0f} | method={method}")

    actions = []
    if is_admin:
        actions.append("Access admin endpoint with low-privilege session token")
        actions.append("Modify role/user_type parameter in request body/headers")
    if is_internal:
        actions.append("Set X-Forwarded-For/X-Real-IP to internal ranges")
        actions.append("Add X-Internal: true header and retry")
    actions.append("Test HTTP method override headers (X-HTTP-Method-Override)")
    actions.append("Check for missing admin checks on sub-endpoints")

    ep_id = int(ep.get("id", 0))
    return Hypothesis(
        id=_hyp_id("priv_esc", ep_id),
        vulnerability_type=VulnerabilityType.PRIVILEGE_ESCALATION,
        target_id=target_id,
        target_name=target_name,
        endpoint=ep,
        likelihood=0.55 if is_admin else 0.3,
        impact=0.9,
        exploitability=0.45,
        confidence=0.0,
        priority_score=0.0,
        evidence=evidence,
        reasoning=f"Admin/internal endpoint detected — verify authorization at the role level, not just the UI layer.",
        suggested_actions=actions,
        source=HypothesisSource.RULE,
        vector="Privilege escalation",
        attack_surface_labels=surface,
    )


def generate_data_exposure(
    ep: Dict[str, Any], target_id: int, target_name: str,
) -> Optional[Hypothesis]:
    path: str = str(ep.get("path", ""))
    method: str = str(ep.get("method", "GET")).upper()
    signals: List[str] = ep.get("signals", [])
    labels: List[str] = ep.get("labels", [])
    surface: List[str] = ep.get("attack_surface", [])
    risk_score: float = float(ep.get("risk_score", 0))
    lower = path.lower()

    has_export_signal = (
        "data_exfiltration" in surface
        or "export" in labels
        or any(s in signals for s in {"export", "billing", "identity", "data_exposure"})
        or any(kw in lower for kw in {"export", "download", "report", "csv", "pdf", "backup", "billing", "invoice"})
    )
    if not has_export_signal:
        return None

    is_billing = "billing" in signals or "billing" in lower
    is_identity = "identity" in signals or any(kw in lower for kw in {"profile", "user", "account"})

    evidence = []
    if is_billing:
        evidence.append("Billing endpoint — payment data, invoices, subscription details")
    if is_identity:
        evidence.append("Identity endpoint — PII, emails, phone numbers, address data")
    evidence.append(f"Export/Data download endpoint — sensitive data may be leaked")
    evidence.append(f"risk_score={risk_score:.0f} | method={method}")

    sensitivity_base = 0.75 if is_billing else (0.7 if is_identity else 0.5)

    actions = []
    if is_billing:
        actions.append("Access billing endpoint of another user by modifying identifiers")
        actions.append("Check if invoice PDFs contain full payment card numbers")
    actions.append("Download exported data and inspect for PII, tokens, or internal data")
    actions.append("Test pagination/range parameters for data leakage beyond authorized scope")
    actions.append("Check response for sensitive fields not shown in UI")

    ep_id = int(ep.get("id", 0))
    return Hypothesis(
        id=_hyp_id("data_exposure", ep_id),
        vulnerability_type=VulnerabilityType.DATA_EXPOSURE,
        target_id=target_id,
        target_name=target_name,
        endpoint=ep,
        likelihood=0.65,
        impact=sensitivity_base,
        exploitability=0.6,
        confidence=0.0,
        priority_score=0.0,
        evidence=evidence,
        reasoning=f"Data export/sensitive data endpoint — inspect response for PII, billing data, or internal information beyond authorization scope.",
        suggested_actions=actions,
        source=HypothesisSource.RULE,
        vector="Data exposure",
        attack_surface_labels=surface,
    )


def generate_graphql(
    ep: Dict[str, Any], target_id: int, target_name: str,
) -> Optional[Hypothesis]:
    path: str = str(ep.get("path", ""))
    method: str = str(ep.get("method", "GET")).upper()
    signals: List[str] = ep.get("signals", [])
    labels: List[str] = ep.get("labels", [])
    surface: List[str] = ep.get("attack_surface", [])
    risk_score: float = float(ep.get("risk_score", 0))
    lower = path.lower()

    if "graphql" not in labels and "graphql" not in lower:
        return None

    evidence = []
    evidence.append("GraphQL endpoint detected")

    has_batching = any(kw in lower for kw in {"batch", "aliases"})
    has_auth = "authentication_surface" in surface

    if has_batching:
        evidence.append("Batching capability — possible brute-force/rate-limit bypass via aliases")
    if has_auth:
        evidence.append("Auth surface overlaps GraphQL — check for missing field-level auth")
    evidence.append(f"risk_score={risk_score:.0f}")

    actions = []
    actions.append("Send introspection query to dump full schema")
    actions.append("Query __schema { types { name fields { name } } }")
    if has_batching:
        actions.append("Send batch query with aliases to bypass rate limits in a single request")
    actions.append("Test for deep/recursive query that causes resource exhaustion")
    actions.append("Check if mutations require proper authorization")
    actions.append("Test for field-level authorization gaps by querying nested objects")
    actions.append("Check for GraphQL-specific access control: __typename, isAuthenticated fields")

    ep_id = int(ep.get("id", 0))
    return Hypothesis(
        id=_hyp_id("graphql", ep_id),
        vulnerability_type=VulnerabilityType.GRAPHQL_INTROSPECTION,
        target_id=target_id,
        target_name=target_name,
        endpoint=ep,
        likelihood=0.8,
        impact=0.7,
        exploitability=0.85,
        confidence=0.0,
        priority_score=0.0,
        evidence=evidence,
        reasoning="GraphQL endpoint — introspection is enabled by default. Dump schema to map entire data model, then probe for field-level auth gaps.",
        suggested_actions=actions,
        source=HypothesisSource.RULE,
        vector="GraphQL logic",
        attack_surface_labels=surface,
    )


def generate_business_logic(
    ep: Dict[str, Any], target_id: int, target_name: str,
) -> Optional[Hypothesis]:
    path: str = str(ep.get("path", ""))
    method: str = str(ep.get("method", "GET")).upper()
    signals: List[str] = ep.get("signals", [])
    labels: List[str] = ep.get("labels", [])
    risk_score: float = float(ep.get("risk_score", 0))
    lower = path.lower()

    has_logic_signals = (
        any(kw in lower for kw in {"transfer", "payment", "refund", "coupon", "discount", "credit", "wallet", "balance", "order", "checkout", "purchase"})
        or "web3" in labels
        or any(s in signals for s in {"web3"})
    )
    if not has_logic_signals:
        return None

    is_financial = any(kw in lower for kw in {"transfer", "payment", "refund", "wallet", "balance", "credit"})
    is_order = any(kw in lower for kw in {"order", "checkout", "purchase", "coupon", "discount"})
    is_web3 = "web3" in labels or "web3" in signals

    evidence = []
    if is_financial:
        evidence.append("Financial operation endpoint — test for race conditions and manipulation")
    if is_order:
        evidence.append("Order/e-commerce endpoint — test for price manipulation and logic flaws")
    if is_web3:
        evidence.append("Web3 endpoint — test for signature replay, lack of nonce, missing amount validation")
    evidence.append(f"risk_score={risk_score:.0f} | method={method}")

    actions = []
    if is_financial:
        actions.append("Send duplicate requests to test for race conditions (concurrent transfers)")
        actions.append("Try negative amounts or zero-value transactions")
        actions.append("Test currency/unit manipulation (cents vs dollars)")
    if is_order:
        actions.append("Modify price/quantity fields in POST/PUT requests")
        actions.append("Apply coupon codes multiple times")
        actions.append("Test integer overflow in quantity fields")
    if is_web3:
        actions.append("Capture and replay a signed message to test for nonce validation")
        actions.append("Modify amount field in signed transaction and verify signature verification")

    ep_id = int(ep.get("id", 0))
    return Hypothesis(
        id=_hyp_id("biz_logic", ep_id),
        vulnerability_type=VulnerabilityType.BUSINESS_LOGIC,
        target_id=target_id,
        target_name=target_name,
        endpoint=ep,
        likelihood=0.45,
        impact=0.8 if is_financial else 0.6,
        exploitability=0.55,
        confidence=0.0,
        priority_score=0.0,
        evidence=evidence,
        reasoning=f"Business logic endpoint detected — test for race conditions, price manipulation, and state transition flaws.",
        suggested_actions=actions,
        source=HypothesisSource.RULE,
        vector="Business logic",
        attack_surface_labels=ep.get("attack_surface", []),
    )


def generate_file_operation(
    ep: Dict[str, Any], target_id: int, target_name: str,
) -> Optional[Hypothesis]:
    path: str = str(ep.get("path", ""))
    method: str = str(ep.get("method", "GET")).upper()
    labels: List[str] = ep.get("labels", [])
    surface: List[str] = ep.get("attack_surface", [])
    signals: List[str] = ep.get("signals", [])
    risk_score: float = float(ep.get("risk_score", 0))
    lower = path.lower()

    if "file_operation" not in labels and "upload_surface" not in surface:
        return None

    is_upload = "upload_surface" in surface or "upload" in lower
    is_download = any(kw in lower for kw in {"download", "file", "attachment", "document"})

    evidence = []
    if is_upload:
        evidence.append("File upload endpoint — RCE via filename/path traversal, SSRF via malicious file")
    if is_download:
        evidence.append("File download endpoint — path traversal in filename parameter")
    evidence.append(f"risk_score={risk_score:.0f} | method={method}")

    actions = []
    if is_upload:
        actions.append("Upload file with path traversal in filename (../../etc/passwd)")
        actions.append("Upload executable file type (PHP, JSP, ASPX) and verify execution")
        actions.append("Upload SVG with XXE payload")
        actions.append("Upload file with null-byte injection in filename")
    if is_download:
        actions.append("Use path traversal in download parameter (../../etc/passwd)")
        actions.append("Test for directory listing on file storage paths")

    ep_id = int(ep.get("id", 0))
    return Hypothesis(
        id=_hyp_id("file_op", ep_id),
        vulnerability_type=VulnerabilityType.FILE_OPERATION,
        target_id=target_id,
        target_name=target_name,
        endpoint=ep,
        likelihood=0.5 if is_upload else 0.4,
        impact=0.9 if is_upload else 0.6,
        exploitability=0.5,
        confidence=0.0,
        priority_score=0.0,
        evidence=evidence,
        reasoning=f"File operation endpoint — test for path traversal, unrestricted upload, and SSRF via file processing.",
        suggested_actions=actions,
        source=HypothesisSource.RULE,
        vector="File operation",
        attack_surface_labels=surface,
    )


def generate_web3(
    ep: Dict[str, Any], target_id: int, target_name: str,
) -> Optional[Hypothesis]:
    path: str = str(ep.get("path", ""))
    method: str = str(ep.get("method", "GET")).upper()
    labels: List[str] = ep.get("labels", [])
    signals: List[str] = ep.get("signals", [])
    surface: List[str] = ep.get("attack_surface", [])
    risk_score: float = float(ep.get("risk_score", 0))
    lower = path.lower()

    is_web3 = "web3" in labels or "web3" in signals or any(s in surface for s in {"rpc_surface", "wallet_surface", "signature_surface"})
    if not is_web3:
        return None

    is_rpc = "rpc_surface" in surface or any(kw in lower for kw in {"rpc", "jsonrpc", "eth_", "call", "send"})
    is_wallet = "wallet_surface" in surface or any(kw in lower for kw in {"wallet", "balance", "transfer", "signature", "nonce"})
    is_signature = "signature_surface" in surface or any(kw in lower for kw in {"signature", "sign", "message", "eip"})

    evidence = []
    if is_rpc:
        evidence.append("RPC endpoint — possible unrestricted node access or method enumeration")
    if is_wallet:
        evidence.append("Wallet endpoint — token/balance manipulation risk")
    if is_signature:
        evidence.append("Signature endpoint — signature replay or malleability risk")
    evidence.append(f"risk_score={risk_score:.0f}")

    actions = []
    if is_rpc:
        actions.append("Enumerate available RPC methods via eth_call to non-existent contracts")
        actions.append("Test for unprotected admin RPC methods (miner, admin, personal namespaces)")
    if is_wallet:
        actions.append("Check if wallet balance can be read for any address without auth")
        actions.append("Test transfer endpoint for replay across different chains (Ethereum vs Polygon)")
    if is_signature:
        actions.append("Replay signed message to verify nonce or chain ID enforcement")
        actions.append("Modify signature payload and verify malleability protection")
    actions.append("Test for eth_call to internal contract addresses (0x0..1, 0x0..2)")

    ep_id = int(ep.get("id", 0))
    return Hypothesis(
        id=_hyp_id("web3", ep_id),
        vulnerability_type=VulnerabilityType.WEB3_RPC_LEAK if is_rpc else VulnerabilityType.WEB3_SIGNATURE_REPLAY,
        target_id=target_id,
        target_name=target_name,
        endpoint=ep,
        likelihood=0.5,
        impact=0.8 if is_wallet else 0.6,
        exploitability=0.6,
        confidence=0.0,
        priority_score=0.0,
        evidence=evidence,
        reasoning=f"Web3/crypto endpoint — test for RPC method exposure, signature replay, and wallet manipulation.",
        suggested_actions=actions,
        source=HypothesisSource.RULE,
        vector="Web3",
        attack_surface_labels=surface,
    )


GENERATORS = [
    generate_idor,
    generate_auth_bypass,
    generate_ssrf,
    generate_privilege_escalation,
    generate_data_exposure,
    generate_graphql,
    generate_business_logic,
    generate_file_operation,
    generate_web3,
]


def generate_hypotheses(
    endpoints: List[Dict[str, Any]],
    target_id: int,
    target_name: str,
) -> List[Hypothesis]:
    hypotheses: List[Hypothesis] = []
    seen = set()
    for ep in endpoints:
        for gen in GENERATORS:
            h = gen(ep, target_id, target_name)
            if h is None:
                continue
            if h.id in seen:
                continue
            seen.add(h.id)
            hypotheses.append(h)
    return hypotheses
