import hashlib
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

ID_PATTERNS = [
    re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"),
    re.compile(r"user[_-]?\d+", re.IGNORECASE),
    re.compile(r"org[_-]?\d+", re.IGNORECASE),
    re.compile(r"account[_-]?\d+", re.IGNORECASE),
    re.compile(r"team[_-]?\d+", re.IGNORECASE),
    re.compile(r"member[_-]?\d+", re.IGNORECASE),
    re.compile(r"id[=:]_?(\d+)"),
]


@dataclass
class IdentityLink:
    source_endpoint: str
    target_endpoint: str
    entity_type: str
    confidence: float
    evidence: list[str]


@dataclass
class IdentityToken:
    token: str
    original_value: str
    entity_type: str
    endpoints_seen: list[str] = field(default_factory=list)


class IdentityGraph:
    def __init__(self):
        self._tokens: dict[str, IdentityToken] = {}
        self._reverse: dict[str, str] = {}
        self._links: list[IdentityLink] = []
        self._endpoint_identities: dict[str, set[str]] = defaultdict(set)

    def tokenize(self, raw_value: str, entity_type: str = "unknown", source_endpoint: str | None = None) -> str:
        if raw_value in self._reverse:
            token = self._reverse[raw_value]
            existing = self._tokens[token]
            if source_endpoint and source_endpoint not in existing.endpoints_seen:
                existing.endpoints_seen.append(source_endpoint)
                self._endpoint_identities[source_endpoint].add(token)
            return token

        token = self._generate_token(raw_value)
        self._tokens[token] = IdentityToken(
            token=token,
            original_value=raw_value,
            entity_type=entity_type,
            endpoints_seen=[source_endpoint] if source_endpoint else [],
        )
        self._reverse[raw_value] = token
        if source_endpoint:
            self._endpoint_identities[source_endpoint].add(token)
        return token

    def resolve(self, token: str) -> str | None:
        entry = self._tokens.get(token)
        return entry.original_value if entry else None

    def propagate(self, endpoint_a: str, endpoint_b: str, entity_type: str, evidence: list[str] | None = None) -> IdentityLink:
        link = IdentityLink(
            source_endpoint=endpoint_a,
            target_endpoint=endpoint_b,
            entity_type=entity_type,
            confidence=0.7,
            evidence=evidence or [],
        )
        self._links.append(link)

        shared_tokens = self._endpoint_identities.get(endpoint_a, set()) & self._endpoint_identities.get(endpoint_b, set())
        if shared_tokens:
            link.confidence = min(0.95, link.confidence + 0.1 * len(shared_tokens))

        return link

    def detect_reuse(self, endpoint_ids: list[str]) -> list[dict[str, Any]]:
        reuse_chains: list[dict[str, Any]] = []
        seen_pairs: set[tuple] = set()

        for i, ep_a in enumerate(endpoint_ids):
            for j in range(i + 1, len(endpoint_ids)):
                ep_b = endpoint_ids[j]
                tokens_a = self._endpoint_identities.get(ep_a, set())
                tokens_b = self._endpoint_identities.get(ep_b, set())
                shared = tokens_a & tokens_b

                if shared and (ep_a, ep_b) not in seen_pairs and (ep_b, ep_a) not in seen_pairs:
                    seen_pairs.add((ep_a, ep_b))
                    reuse_chains.append({
                        "endpoint_a": ep_a,
                        "endpoint_b": ep_b,
                        "shared_tokens": list(shared),
                        "confidence": min(0.5 + 0.1 * len(shared), 0.95),
                    })

        return reuse_chains

    def get_identity_for_endpoint(self, endpoint_id: str) -> list[IdentityToken]:
        token_keys = self._endpoint_identities.get(endpoint_id, set())
        return [self._tokens[t] for t in token_keys if t in self._tokens]

    def scan_for_identities(self, path: str, params: dict[str, Any] | None = None, body: str | None = None) -> dict[str, str]:
        found: dict[str, str] = {}
        text = f"{path} {str(params or {})} {body or ''}"

        for pattern in ID_PATTERNS:
            matches = pattern.findall(text)
            for m in matches:
                raw = m if isinstance(m, str) else m[0]
                entity_type = "uuid" if "-" in raw else "numeric_id"
                found[raw] = entity_type

        return found

    def link_endpoints_by_identity(self, endpoint_map: dict[str, dict[str, Any]]) -> list[IdentityLink]:
        links: list[IdentityLink] = []
        eid_list = list(endpoint_map.keys())

        for i, eid_a in enumerate(eid_list):
            ep_a = endpoint_map[eid_a]
            for j in range(i + 1, len(eid_list)):
                eid_b = eid_list[j]
                ep_b = endpoint_map[eid_b]

                shared_entity = None
                for entity_type in ("user", "account", "organization", "team"):
                    if entity_type in str(ep_a.get("path", "")).lower() and entity_type in str(ep_b.get("path", "")).lower():
                        shared_entity = entity_type
                        break

                if shared_entity:
                    link = self.propagate(eid_a, eid_b, shared_entity, evidence=[f"Both reference entity:{shared_entity}"])
                    links.append(link)

        return links

    def to_dict(self) -> dict[str, Any]:
        return {
            "tokens": {k: {"original": v.original_value, "entity_type": v.entity_type, "endpoints": v.endpoints_seen} for k, v in self._tokens.items()},
            "links": [{"source": link.source_endpoint, "target": link.target_endpoint, "entity": link.entity_type, "confidence": link.confidence, "evidence": link.evidence} for link in self._links],
            "endpoint_identities": {k: list(v) for k, v in self._endpoint_identities.items()},
        }

    def _generate_token(self, raw_value: str) -> str:
        h = hashlib.sha256(raw_value.encode()).hexdigest()[:12]
        return f"id_{h}"
