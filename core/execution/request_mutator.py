import copy
import re
from typing import Any, Dict, List, Optional, Tuple

from core.validation.replayer import AuthContext, RequestSpec

PARAM_PATTERN = re.compile(r"\{(\w+)\}")


class RequestMutator:
    def build_mutations(
        self, attack_vector: str, path: str, params: Dict[str, str]
    ) -> Dict[str, str]:
        if attack_vector == "IDOR":
            return self._idor_mutations(params)
        if attack_vector in ("Auth bypass", "Privilege escalation"):
            return self._auth_bypass_mutations()
        if attack_vector == "Data exposure":
            return self._data_exposure_mutations(params)
        if attack_vector == "GraphQL logic":
            return self._graphql_mutations()
        if attack_vector == "Business logic":
            return self._business_logic_mutations(params)
        return {}

    def build_auth_contexts(
        self,
        attack_vector: str,
        baseline_token: Optional[str] = None,
        probe_token: Optional[str] = None,
    ) -> Tuple[AuthContext, AuthContext]:
        if attack_vector == "Auth bypass":
            return (
                AuthContext(token=baseline_token, label="authenticated"),
                AuthContext(label="anonymous"),
            )
        return (
            AuthContext(token=baseline_token, label="user_a"),
            AuthContext(token=probe_token or baseline_token, label="user_b"),
        )

    def mutate_request_spec(
        self,
        spec: RequestSpec,
        mutations: Dict[str, str],
    ) -> RequestSpec:
        mutated = RequestSpec(
            url=self._mutate_url(spec.url, mutations),
            method=spec.method,
            headers=dict(spec.headers),
            params=dict(spec.params),
            body=spec.body,
        )
        for key, val in mutations.items():
            if key in spec.params:
                mutated.params[key] = val
        return mutated

    def build_curl(self, spec: RequestSpec, auth: AuthContext) -> str:
        parts = ["curl"]
        if spec.method != "GET":
            parts.append(f"-X {spec.method}")
        if auth.token:
            parts.append(f"-H 'Authorization: Bearer {auth.token}'")
        for k, v in spec.headers.items():
            parts.append(f"-H '{k}: {v}'")
        for k, v in spec.params.items():
            parts.append(f"-d '{k}={v}'" if spec.method in ("POST", "PUT", "PATCH") else "")
        parts.append(f"'{spec.url}'")
        return " \\\n  ".join(parts)

    def _idor_mutations(self, params: Dict[str, str]) -> Dict[str, str]:
        mutations: Dict[str, str] = {}
        for key in params:
            lower = key.lower()
            if any(tok in lower for tok in ["id", "uid", "user", "account", "order", "org", "tenant", "team"]):
                mutations[key] = self._swap_id(params[key])
        return mutations

    def _auth_bypass_mutations(self) -> Dict[str, str]:
        return {}

    def _data_exposure_mutations(self, params: Dict[str, str]) -> Dict[str, str]:
        mutations: Dict[str, str] = {}
        for key in params:
            if any(tok in key.lower() for tok in ["limit", "offset", "page", "export", "format"]):
                mutations[key] = "all" if "format" in key.lower() else "9999"
        return mutations

    def _graphql_mutations(self) -> Dict[str, str]:
        return {}

    def _business_logic_mutations(self, params: Dict[str, str]) -> Dict[str, str]:
        mutations: Dict[str, str] = {}
        for key in params:
            lower = key.lower()
            if any(tok in lower for tok in ["role", "admin", "type", "level", "access"]):
                mutations[key] = "admin"
            if any(tok in lower for tok in ["amount", "price", "quantity", "total"]):
                mutations[key] = "0"
            if any(tok in lower for tok in ["approved", "status", "state"]):
                mutations[key] = "approved"
        return mutations

    def _mutate_url(self, url: str, mutations: Dict[str, str]) -> str:
        result = url
        for key, val in mutations.items():
            result = result.replace(f"{{{key}}}", val)
        return result

    @staticmethod
    def _swap_id(current: str) -> str:
        try:
            n = int(current)
            return str(n + 1)
        except ValueError:
            return current[::-1]
