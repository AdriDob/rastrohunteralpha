import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("rastro.web3.adapter")

CHAIN_IDENTIFIERS = {
    "ethereum": ["ethereum", "eth", "mainnet", "0x1"],
    "solana": ["solana", "sol", "svm"],
    "polygon": ["polygon", "matic", "0x89"],
    "arbitrum": ["arbitrum", "arb", "0xa4b1"],
    "optimism": ["optimism", "op", "0xa"],
    "base": ["base", "0x2105"],
    "bnb": ["bnb", "bsc", "binance", "0x38"],
    "avalanche": ["avalanche", "avax", "0xa86a"],
}

RPC_METHOD_PATTERNS = [
    "eth_", "net_", "web3_", "debug_", "trace_",
    "admin_", "personal_", "txpool_", "miner_",
    "sol_", "getProgramAccounts", "getTokenAccounts",
]

CONTRACT_ADDRESS_PATTERN = re.compile(r"0x[a-fA-F0-9]{40}")

SIGNATURE_HEADERS = [
    "x-signature", "x-sign", "x-signature-version",
    "x-timestamp", "x-nonce", "x-message",
    "authorization", "x-api-key", "x-wallet-signature",
]

WALLET_KEYWORDS = [
    "wallet", "balance", "transfer", "send", "tx", "transaction",
    "sign", "verify", "nonce", "signature", "message",
    "approve", "allowance", "deposit", "withdraw", "stake",
    "swap", "mint", "burn", "bridge", "claim",
]

RPC_ENDPOINTS = [
    "/rpc", "/v1/rpc", "/v2/rpc", "/api/rpc",
    "/infura", "/alchemy", "/quicknode",
    "/solana", "/api/v2/solana",
]

JSON_RPC_KEYWORDS = [
    "jsonrpc", "2.0", "method", "params", "id",
]


class Web3EntityType(str, Enum):
    CONTRACT_CALL = "contract_call"
    RPC_METHOD = "rpc_method"
    SIGNATURE_AUTH = "signature_auth"
    WALLET_OPERATION = "wallet_operation"
    ONCHAIN_QUERY = "onchain_query"


class Web3VulnType(str, Enum):
    REPLAY_ATTACK = "replay_attack"
    SIGNATURE_REUSE = "signature_reuse"
    CONTRACT_STATE_ASSUMPTION = "contract_state_assumption"
    NONCE_REUSE = "nonce_reuse"
    UNAUTHORIZED_RPC = "unauthorized_rpc"
    WALLET_DISCLOSURE = "wallet_disclosure"


@dataclass
class Web3Vulnerability:
    vuln_type: Web3VulnType
    confidence: float
    description: str
    poc_curl_template: str


@dataclass
class Web3Target:
    target_type: Web3EntityType
    chain: str | None = None
    contract_address: str | None = None
    method_signature: str | None = None
    rpc_method: str | None = None
    is_authenticated: bool = False
    wallet_keywords_found: list[str] = field(default_factory=list)

    def to_entity_node(self) -> dict[str, Any]:
        return {
            "node_id": f"web3_entity:{self.target_type.value}",
            "type": "web3_entity",
            "value": self.target_type.value,
            "metadata": {
                "chain": self.chain or "unknown",
                "contract_address": self.contract_address,
                "method_signature": self.method_signature,
                "rpc_method": self.rpc_method,
                "is_authenticated": self.is_authenticated,
                "wallet_keywords": self.wallet_keywords_found,
            },
        }


class Web3Adapter:
    def detect(self, path: str, method: str, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> Web3Target | None:
        safe_path = str(path or "/")
        safe_params = params or {}
        safe_headers = headers or {}
        lower_path = safe_path.lower()

        chain = self._detect_chain(lower_path, safe_params)

        # RPC endpoint
        if any(rpc in lower_path for rpc in RPC_ENDPOINTS):
            return self._classify_rpc(safe_path, method, safe_params, safe_headers, chain)

        # Contract address in path
        contract_match = CONTRACT_ADDRESS_PATTERN.search(safe_path)
        if contract_match:
            return self._classify_contract(safe_path, method, safe_params, safe_headers, contract_match.group(0), chain)

        # Signature headers (check before JSON-RPC / wallet to avoid misclassification)
        for sig_header in SIGNATURE_HEADERS:
            if any(sig_header in str(k).lower() for k in safe_headers):
                return self._classify_signature_auth(safe_path, method, safe_params, safe_headers, chain)

        # JSON-RPC body
        if method == "POST" and safe_params:
            return self._classify_jsonrpc(safe_path, method, safe_params, safe_headers, chain)

        # Wallet/signature keywords
        wallet_kw = [kw for kw in WALLET_KEYWORDS if kw in lower_path or any(kw in str(p).lower() for p in safe_params.values())]
        if wallet_kw:
            return self._classify_wallet(safe_path, method, safe_params, safe_headers, wallet_kw, chain)

        return None

    def analyze_vulnerabilities(self, target: Web3Target, path: str, method: str, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> list[Web3Vulnerability]:
        vulns: list[Web3Vulnerability] = []
        safe_params = params or {}
        safe_headers = headers or {}

        if target.target_type == Web3EntityType.RPC_METHOD:
            vulns.extend(self._rpc_vulnerabilities(target, safe_headers))
        elif target.target_type == Web3EntityType.SIGNATURE_AUTH:
            vulns.extend(self._signature_vulnerabilities(target, safe_params, safe_headers))
        elif target.target_type == Web3EntityType.CONTRACT_CALL:
            vulns.extend(self._contract_vulnerabilities(target, safe_params))
        elif target.target_type == Web3EntityType.WALLET_OPERATION:
            vulns.extend(self._wallet_vulnerabilities(target, safe_params))

        return vulns

    def _detect_chain(self, lower_path: str, params: dict[str, Any]) -> str | None:
        combined = f"{lower_path} {str(params).lower()}"
        for chain_name, identifiers in CHAIN_IDENTIFIERS.items():
            if any(ident in combined for ident in identifiers):
                return chain_name
        return None

    def _classify_rpc(self, path: str, method: str, params: dict[str, Any], headers: dict[str, str], chain: str | None) -> Web3Target:
        rpc_method = None
        if isinstance(params, dict):
            rpc_method = params.get("method") or params.get("jsonrpc_method")
        if isinstance(params, str) and "method" in str(params):
            try:
                import json
                parsed = json.loads(params)
                rpc_method = parsed.get("method")
            except (json.JSONDecodeError, ValueError, TypeError):
                logger.warning("Failed to parse RPC params as JSON", exc_info=True)

        return Web3Target(
            target_type=Web3EntityType.RPC_METHOD,
            chain=chain,
            rpc_method=str(rpc_method) if rpc_method else "unknown",
            is_authenticated=bool(headers.get("Authorization")),
        )

    def _classify_contract(self, path: str, method: str, params: dict[str, Any], headers: dict[str, str], contract_address: str, chain: str | None) -> Web3Target:
        method_sig = None
        lower_path = path.lower()
        for func in ["transfer", "balanceOf", "approve", "allowance", "mint", "burn", "swap"]:
            if func in lower_path:
                method_sig = func
                break

        return Web3Target(
            target_type=Web3EntityType.CONTRACT_CALL,
            chain=chain,
            contract_address=contract_address,
            method_signature=method_sig,
            is_authenticated="sign" in str(headers).lower() or bool(headers.get("Authorization")),
        )

    def _classify_jsonrpc(self, path: str, method: str, params: dict[str, Any], headers: dict[str, str], chain: str | None) -> Web3Target:
        body_str = str(params)
        if all(kw in body_str for kw in JSON_RPC_KEYWORDS):
            return Web3Target(
                target_type=Web3EntityType.RPC_METHOD,
                chain=chain,
                rpc_method="jsonrpc",
                is_authenticated=bool(headers.get("Authorization")),
            )
        return Web3Target(
            target_type=Web3EntityType.RPC_METHOD,
            chain=chain,
            rpc_method="unknown",
            is_authenticated=bool(headers.get("Authorization")),
        )

    def _classify_wallet(self, path: str, method: str, params: dict[str, Any], headers: dict[str, str], wallet_kw: list[str], chain: str | None) -> Web3Target:
        return Web3Target(
            target_type=Web3EntityType.WALLET_OPERATION,
            chain=chain,
            wallet_keywords_found=wallet_kw,
            is_authenticated=bool(headers.get("Authorization") or headers.get("x-signature")),
        )

    def _classify_signature_auth(self, path: str, method: str, params: dict[str, Any], headers: dict[str, str], chain: str | None) -> Web3Target:
        return Web3Target(
            target_type=Web3EntityType.SIGNATURE_AUTH,
            chain=chain,
            is_authenticated=True,
        )

    def _rpc_vulnerabilities(self, target: Web3Target, headers: dict[str, str]) -> list[Web3Vulnerability]:
        vulns: list[Web3Vulnerability] = []
        if target.rpc_method in ("eth_getStorageAt", "debug_traceTransaction", "personal_unlockAccount"):
            vulns.append(Web3Vulnerability(
                vuln_type=Web3VulnType.UNAUTHORIZED_RPC,
                confidence=0.45,
                description=f"Sensitive RPC method '{target.rpc_method}' exposed. May leak on-chain data or allow unauthorized node control.",
                poc_curl_template=f"curl -X POST '<rpc_url>' -H 'Content-Type: application/json' -d '{{\"jsonrpc\":\"2.0\",\"method\":\"{target.rpc_method}\",\"params\":[],\"id\":1}}'",
            ))
        if not target.is_authenticated:
            vulns.append(Web3Vulnerability(
                vuln_type=Web3VulnType.UNAUTHORIZED_RPC,
                confidence=0.35,
                description="Unauthenticated RPC endpoint. Attacker can query chain state without credentials.",
                poc_curl_template="curl -X POST '<rpc_url>' -H 'Content-Type: application/json' -d '{\"jsonrpc\":\"2.0\",\"method\":\"eth_blockNumber\",\"params\":[],\"id\":1}'",
            ))
        return vulns

    def _signature_vulnerabilities(self, target: Web3Target, params: dict[str, Any], headers: dict[str, str]) -> list[Web3Vulnerability]:
        vulns: list[Web3Vulnerability] = []
        has_nonce = any("nonce" in str(k).lower() for k in headers) or any("nonce" in str(k).lower() for k in params)
        has_timestamp = any("timestamp" in str(k).lower() for k in headers) or any("timestamp" in str(k).lower() for k in params)

        if not has_nonce and not has_timestamp:
            vulns.append(Web3Vulnerability(
                vuln_type=Web3VulnType.REPLAY_ATTACK,
                confidence=0.55,
                description="Signature-based auth without nonce or timestamp. Requests can be replayed by an attacker who captures the payload.",
                poc_curl_template="curl -X POST '<endpoint>' -H 'x-signature: <captured_signature>' -d '{\"action\":\"repeat\"}'",
            ))
        if not has_nonce:
            vulns.append(Web3Vulnerability(
                vuln_type=Web3VulnType.NONCE_REUSE,
                confidence=0.40,
                description="No nonce detected in signature auth. Cannot detect replay if nonce is missing or static.",
                poc_curl_template="curl -X POST '<endpoint>' -H 'x-signature: <same_signature>' -d '{\"action\":\"repeat_twice\"}'",
            ))
        return vulns

    def _contract_vulnerabilities(self, target: Web3Target, params: dict[str, Any]) -> list[Web3Vulnerability]:
        vulns: list[Web3Vulnerability] = []
        if target.method_signature in ("transfer", "approve"):
            vulns.append(Web3Vulnerability(
                vuln_type=Web3VulnType.CONTRACT_STATE_ASSUMPTION,
                confidence=0.50,
                description=f"Contract call to '{target.method_signature}' without explicit authorization boundary check. May assume caller identity without validation.",
                poc_curl_template=f"curl -X POST '<endpoint>' -H 'Content-Type: application/json' -d '{{\"to\":\"{target.contract_address or '0x...'}\",\"function\":\"{target.method_signature}\"}}'",
            ))
        if "owner" in str(params) or "admin" in str(params):
            vulns.append(Web3Vulnerability(
                vuln_type=Web3VulnType.CONTRACT_STATE_ASSUMPTION,
                confidence=0.45,
                description="Owner/admin parameter modifiable in contract call. May allow unauthorized state mutation.",
                poc_curl_template="curl -X POST '<endpoint>' -d '{\"owner\":\"<attacker_address>\"}'",
            ))
        return vulns

    def _wallet_vulnerabilities(self, target: Web3Target, params: dict[str, Any]) -> list[Web3Vulnerability]:
        vulns: list[Web3Vulnerability] = []
        if "balance" in target.wallet_keywords_found:
            vulns.append(Web3Vulnerability(
                vuln_type=Web3VulnType.WALLET_DISCLOSURE,
                confidence=0.35,
                description="Wallet balance endpoint may leak financial information across users if IDOR exists.",
                poc_curl_template="curl -X GET '<endpoint>/balance?address=0x<other_user_address>'",
            ))
        if "sign" in target.wallet_keywords_found:
            vulns.append(Web3Vulnerability(
                vuln_type=Web3VulnType.SIGNATURE_REUSE,
                confidence=0.40,
                description="Signing endpoint may allow signature reuse across contexts if message is not domain-bound.",
                poc_curl_template="curl -X POST '<endpoint>/sign' -d '{\"message\":\"<captured_message>\"}'",
            ))
        return vulns
