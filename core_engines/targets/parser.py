import logging
import re
from urllib.parse import urlparse

logger = logging.getLogger("rastro.targets.parser")

DOMAIN_RE = re.compile(r"(?:\*\.)?([A-Za-z0-9.-]+\.[A-Za-z]{2,})")


def extract_domains_from_scope(scope: str) -> list[str]:
    domains = []
    # try url parse
    try:
        parsed = urlparse(scope if scope.startswith("http") else "//" + scope)
        host = parsed.hostname
        if host:
            domains.append(host.lower())
    except Exception:
        logger.warning("Failed to parse scope as URL", exc_info=True)

    # fallback regex
    for m in DOMAIN_RE.finditer(scope):
        d = m.group(1).lower()
        if d not in domains:
            domains.append(d)

    return domains


def is_wildcard_scope(scope: str) -> bool:
    return scope.strip().startswith("*.") or "*." in scope


def is_api_scope(scope: str) -> bool:
    s = scope.lower()
    return "/api" in s or s.endswith("/api") or ".api." in s


def is_graphql_scope(scope: str) -> bool:
    s = scope.lower()
    return "graphql" in s or "gql" in s


def parse_scope(scope_text: str) -> dict:
    domains = extract_domains_from_scope(scope_text)
    return {
        "scope_text": scope_text,
        "domains": domains,
        "is_wildcard": is_wildcard_scope(scope_text),
        "is_api": is_api_scope(scope_text),
        "is_graphql": is_graphql_scope(scope_text),
    }


def parse_program_scopes(scopes: list[str]) -> list[dict]:
    return [parse_scope(s) for s in scopes if s and s.strip()]
