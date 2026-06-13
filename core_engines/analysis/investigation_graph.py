import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


UUID_PATTERN = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)

ENTITY_PATTERNS: Dict[str, List[str]] = {
    "user": ["user", "users", "profile", "member", "members"],
    "account": ["account", "accounts"],
    "organization": ["org", "organization", "organizations", "company"],
    "team": ["team", "teams"],
    "project": ["project", "projects"],
    "workspace": ["workspace", "workspaces"],
    "file": ["file", "files", "attachment", "attachments", "document", "documents", "upload"],
    "billing": ["billing", "invoice", "invoices", "payment", "payments", "subscription"],
    "admin": ["admin", "dashboard", "management", "superuser", "staff"],
    "auth": ["auth", "login", "signin", "signup", "oauth", "session", "token", "apikey", "jwt"],
    "export": ["export", "download", "report", "reports", "csv", "pdf", "backup"],
    "audit": ["audit", "log", "logs", "activity"],
    "notification": ["notification", "notifications", "webhook", "webhooks"],
    "search": ["search", "query"],
    "config": ["config", "configuration", "settings", "preferences"],
    "web3_entity": [
        "wallet", "balance", "transfer", "tx", "transaction",
        "signature", "nonce", "rpc", "infura", "alchemy",
        "contract", "ethereum", "solana", "web3", "chain",
        "eth_", "jsonrpc",
    ],
}

ENTITY_SIGNAL_MAP: Dict[str, str] = {
    "user": "idor",
    "account": "idor",
    "organization": "multi_tenant",
    "team": "multi_tenant",
    "workspace": "multi_tenant",
    "billing": "data_exposure",
    "file": "data_exposure",
    "export": "data_exposure",
    "admin": "admin",
    "auth": "auth",
    "project": "idor",
    "web3_entity": "web3",
}

CLUSTER_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "name": "IDOR",
        "labels": ["id_parameter"],
        "surfaces": ["idor_candidate"],
        "signals": ["idor_params", "uuid", "numeric_id", "auth_smell", "object_reference_param", "ownership_risk"],
        "entities": ["user", "account", "project"],
        "description": "Endpoints con referencias directas a objetos: posible IDOR/BOLA.",
    },
    {
        "name": "Auth",
        "labels": ["auth"],
        "surfaces": ["authentication_surface"],
        "signals": ["auth"],
        "entities": ["auth"],
        "description": "Endpoints de autenticación: puerta de entrada al sistema.",
    },
    {
        "name": "Multi-tenant",
        "labels": ["multi_tenant"],
        "surfaces": ["tenant_boundary"],
        "signals": ["multi_tenant"],
        "entities": ["organization", "team", "workspace"],
        "description": "Endpoints multi-tenant: posible violación de límites entre inquilinos.",
    },
    {
        "name": "Data exposure",
        "labels": ["export"],
        "surfaces": ["data_exfiltration"],
        "signals": ["export"],
        "entities": ["export", "billing", "file"],
        "description": "Endpoints de exportación/descarga: posible fuga de datos sensibles.",
    },
    {
        "name": "GraphQL",
        "labels": ["graphql"],
        "surfaces": ["graphql_attack_surface"],
        "signals": ["graphql"],
        "entities": [],
        "description": "Endpoint GraphQL: superficie de ataque amplia por consultas arbitrarias.",
    },
    {
        "name": "Admin",
        "labels": ["admin"],
        "surfaces": ["admin_surface"],
        "signals": ["admin"],
        "entities": ["admin"],
        "description": "Endpoints administrativos: posible escalada de privilegios.",
    },
    {
        "name": "File operation",
        "labels": ["file_operation"],
        "surfaces": ["upload_surface"],
        "signals": ["file_operation"],
        "entities": ["file"],
        "description": "Endpoints de carga/archivos: posible RCE, path traversal o SSRF.",
    },
    {
        "name": "Web3",
        "labels": ["web3"],
        "surfaces": ["rpc_surface", "wallet_surface", "signature_surface"],
        "signals": ["web3"],
        "entities": ["web3_entity"],
        "description": "Endpoints Web3/Crypto: RPC calls, smart contracts, wallet operations, signature-based auth.",
    },
]

HOT_PATH_TEMPLATES: List[Dict[str, Any]] = [
    {
        "name": "idor_from_auth",
        "start_cluster": "Auth",
        "bridge_entity": "user",
        "end_cluster": "IDOR",
        "reward": "high",
        "template": "Autenticación → {user} → IDOR: autenticarse y modificar referencia de objeto para acceder a recursos ajenos.",
    },
    {
        "name": "bola_tenant_cross",
        "start_cluster": "Multi-tenant",
        "bridge_entity": "organization",
        "end_cluster": "IDOR",
        "reward": "high",
        "template": "Contexto multi-tenant → {organization} → IDOR: cambiar identificador de organización para acceder a datos de otro inquilino (BOLA).",
    },
    {
        "name": "graphql_data_exposure",
        "start_cluster": "GraphQL",
        "bridge_entity": "billing",
        "end_cluster": "Data exposure",
        "reward": "high",
        "template": "GraphQL → {billing} → Exportación: consultar facturación/datos sensibles vía GraphQL sin filtrado adecuado.",
    },
    {
        "name": "privilege_escalation",
        "start_cluster": "Auth",
        "bridge_entity": "admin",
        "end_cluster": "Admin",
        "reward": "high",
        "template": "Autenticación → {admin} → Administración: escalar desde usuario estándar a operaciones administrativas.",
    },
    {
        "name": "idor_file_access",
        "start_cluster": "IDOR",
        "bridge_entity": "file",
        "end_cluster": "File operation",
        "reward": "medium",
        "template": "IDOR → {file} → Archivos: manipular ID de archivo para acceder a documentos de otros usuarios.",
    },
    {
        "name": "tenant_data_leak",
        "start_cluster": "Multi-tenant",
        "bridge_entity": "billing",
        "end_cluster": "Data exposure",
        "reward": "high",
        "template": "Multi-tenant → {billing} → Exportación: extraer facturación de otros inquilinos violando límites de tenant.",
    },
    {
        "name": "graphql_idor_walk",
        "start_cluster": "GraphQL",
        "bridge_entity": "user",
        "end_cluster": "IDOR",
        "reward": "high",
        "template": "GraphQL → {user} → IDOR: enumerar usuarios vía GraphQL con identificadores secuenciales.",
    },
    {
        "name": "auth_session_export",
        "start_cluster": "Auth",
        "bridge_entity": "export",
        "end_cluster": "Data exposure",
        "reward": "medium",
        "template": "Autenticación → {export} → Exportación: usar sesión autenticada para exportar datos masivos sin autorización.",
    },
    {
        "name": "web3_signature_replay",
        "start_cluster": "Web3",
        "bridge_entity": "web3_entity",
        "end_cluster": "Auth",
        "reward": "high",
        "template": "Web3 → {web3_entity} → Autenticación: firmas sin nonce/timestamp reutilizables en endpoints de autenticación Web3.",
    },
    {
        "name": "web3_rpc_data_exposure",
        "start_cluster": "Web3",
        "bridge_entity": "web3_entity",
        "end_cluster": "Data exposure",
        "reward": "high",
        "template": "Web3 → {web3_entity} → Exportación: RPC expuesto filtra estado de contratos o datos de wallet sin autenticación.",
    },
]


@dataclass
class Cluster:
    name: str
    endpoints: List[Dict[str, Any]]
    confidence: float
    reasoning: List[str]


@dataclass
class HotPath:
    nodes: List[str]
    why_it_matters: str
    estimated_reward: str


@dataclass
class InvestigationReport:
    graph: Dict[str, List[Any]]
    clusters: List[Cluster]
    hot_paths: List[HotPath]


class NodeExtractor:
    """
    Extracts graph nodes from scored endpoints:
      - endpoint nodes: each endpoint
      - entity nodes: logical resources (user, org, file, billing, etc.)
      - signal nodes: risk signals (idor, auth, graphql, etc.)
    """

    def extract(
        self, scored_endpoints: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, List[str]]]:
        nodes: List[Dict[str, Any]] = []
        endpoint_ids: List[str] = []
        entity_endpoints: Dict[str, List[str]] = defaultdict(list)

        seen_entities: Set[str] = set()
        seen_signals: Set[str] = set()

        for idx, ep in enumerate(scored_endpoints):
            path = str(ep.get("path", "/"))
            method = str(ep.get("method", "GET")).upper()
            node_id = f"endpoint:{method}:{path}"

            nodes.append({
                "node_id": node_id,
                "type": "endpoint",
                "value": f"{method} {path}",
                "metadata": {
                    "method": method,
                    "path": path,
                    "risk_score": float(ep.get("risk_score", 0)),
                    "labels": list(ep.get("labels", [])),
                    "signals": list(ep.get("signals", [])),
                    "attack_surface": list(ep.get("attack_surface", [])),
                    "params": list(ep.get("params", {}).keys()) if isinstance(ep.get("params"), dict) else [],
                },
            })
            endpoint_ids.append(node_id)

            # Entities from path segments
            lower_path = path.lower()
            for entity_name, patterns in ENTITY_PATTERNS.items():
                for pattern in patterns:
                    if f"/{pattern}" in lower_path or lower_path.startswith(f"{pattern}/") or lower_path == pattern:
                        if entity_name not in seen_entities:
                            nodes.append({
                                "node_id": f"entity:{entity_name}",
                                "type": "entity",
                                "value": entity_name,
                                "metadata": {"endpoints_count": 0, "avg_risk_score": 0.0},
                            })
                            seen_entities.add(entity_name)
                        entity_endpoints[entity_name].append(node_id)
                        break

            # Entities from parameter names
            params = ep.get("params", {})
            if isinstance(params, dict):
                for param_key in params.keys():
                    lower_key = param_key.lower()
                    for entity_name, patterns in ENTITY_PATTERNS.items():
                        for pattern in patterns:
                            if pattern in lower_key:
                                if entity_name not in seen_entities:
                                    nodes.append({
                                        "node_id": f"entity:{entity_name}",
                                        "type": "entity",
                                        "value": entity_name,
                                        "metadata": {"endpoints_count": 0, "avg_risk_score": 0.0},
                                    })
                                    seen_entities.add(entity_name)
                                entity_endpoints[entity_name].append(node_id)
                                break

            # Web3 entity nodes from RPC / wallet / signature signals
            if "web3" in ep.get("signals", []):
                we3_id = "web3_entity:web3"
                if we3_id not in seen_entities:
                    nodes.append({
                        "node_id": we3_id,
                        "type": "web3_entity",
                        "value": "Web3 / Crypto endpoint",
                        "metadata": {"endpoints_count": 0, "avg_risk_score": 0.0},
                    })
                    seen_entities.add(we3_id)
                entity_endpoints.setdefault("web3_entity", []).append(node_id)

            # Signals from labels
            labels = ep.get("labels", [])
            for label in labels:
                signal_name = label.replace("_", " ")
                if label not in seen_signals:
                    nodes.append({
                        "node_id": f"signal:{label}",
                        "type": "signal",
                        "value": signal_name,
                        "metadata": {"endpoints_count": 0, "avg_risk_score": 0.0},
                    })
                    seen_signals.add(label)

            # Signals from attack_surface
            for surface in ep.get("attack_surface", []):
                surface_key = surface.replace("_surface", "").replace("_", " ")
                if surface_key not in seen_signals:
                    nodes.append({
                        "node_id": f"signal:{surface_key}",
                        "type": "signal",
                        "value": surface_key,
                        "metadata": {"endpoints_count": 0, "avg_risk_score": 0.0},
                    })
                    seen_signals.add(surface_key)

        # Enrich entity/signal metadata
        risk_by_endpoint = {
            f"endpoint:{e.get('method','GET')}:{e.get('path','/')}": float(e.get("risk_score", 0))
            for e in scored_endpoints
        }

        for node in nodes:
            if node["type"] == "entity":
                nid = node["node_id"]
                entity_name = nid.replace("entity:", "")
                ep_ids = entity_endpoints.get(entity_name, [])
                scores = [risk_by_endpoint.get(eid, 0) for eid in ep_ids]
                node["metadata"]["endpoints_count"] = len(set(ep_ids))
                node["metadata"]["avg_risk_score"] = round(sum(scores) / len(scores), 1) if scores else 0.0

            if node["type"] == "signal":
                signal_key = node["node_id"].replace("signal:", "")
                matching_eps = [
                    e for e in scored_endpoints
                    if signal_key in e.get("labels", [])
                    or signal_key in e.get("attack_surface", [])
                ]
                scores = [float(e.get("risk_score", 0)) for e in matching_eps]
                node["metadata"]["endpoints_count"] = len(matching_eps)
                node["metadata"]["avg_risk_score"] = round(sum(scores) / len(scores), 1) if scores else 0.0

            if node["type"] == "web3_entity":
                entity_name = node["node_id"].replace("web3_entity:", "")
                ep_ids = entity_endpoints.get(entity_name, [])
                scores = [risk_by_endpoint.get(eid, 0) for eid in ep_ids]
                node["metadata"]["endpoints_count"] = len(set(ep_ids))
                node["metadata"]["avg_risk_score"] = round(sum(scores) / len(scores), 1) if scores else 0.0

        return nodes, dict(entity_endpoints)


class RelationshipDetector:
    """
    Detects edges between graph nodes based on:
      - endpoint → entity references
      - endpoint → signal presence
      - entity ↔ entity shared context
      - signal ↔ entity relevance
    """

    def detect(
        self,
        nodes: List[Dict[str, Any]],
        scored_endpoints: List[Dict[str, Any]],
        entity_endpoints: Dict[str, List[str]],
    ) -> List[Dict[str, Any]]:
        edges: List[Dict[str, Any]] = []
        node_map = {n["node_id"]: n for n in nodes}

        endpoint_nodes = {nid: n for nid, n in node_map.items() if n["type"] == "endpoint"}
        entity_nodes = {nid: n for nid, n in node_map.items() if n["type"] == "entity"}
        web3_nodes = {nid: n for nid, n in node_map.items() if n["type"] == "web3_entity"}
        signal_nodes = {nid: n for nid, n in node_map.items() if n["type"] == "signal"}

        # Endpoint → Entity (references)
        for entity_name, ep_ids in entity_endpoints.items():
            entity_id = f"entity:{entity_name}"
            web3_id = f"web3_entity:{entity_name}"
            target_id = None
            if entity_id in entity_nodes:
                target_id = entity_id
            elif web3_id in web3_nodes:
                target_id = web3_id
            if target_id:
                for unique_eid in set(ep_ids):
                    if unique_eid in endpoint_nodes:
                        edges.append({
                            "from": unique_eid,
                            "to": target_id,
                            "relationship": "references",
                        })

        # Endpoint → Signal (has_signal)
        for ep in scored_endpoints:
            eid = f"endpoint:{ep.get('method','GET')}:{ep.get('path','/')}"
            if eid not in endpoint_nodes:
                continue
            for label in ep.get("labels", []):
                sid = f"signal:{label}"
                if sid in signal_nodes:
                    edges.append({
                        "from": eid,
                        "to": sid,
                        "relationship": "has_signal",
                    })
            for surface in ep.get("attack_surface", []):
                surface_key = surface.replace("_surface", "").replace("_", " ")
                sid = f"signal:{surface_key}"
                if sid in signal_nodes:
                    edge_key = (eid, sid, "has_signal")
                    if not any(
                        e["from"] == eid and e["to"] == sid and e["relationship"] == "has_signal"
                        for e in edges
                    ):
                        edges.append({
                            "from": eid,
                            "to": sid,
                            "relationship": "has_signal",
                        })

        # Entity → Entity: shared endpoints bridge
        entity_pairs_seen: Set[Tuple[str, str]] = set()
        entity_list = list(entity_endpoints.items())
        for i, (name_a, eps_a) in enumerate(entity_list):
            for j in range(i + 1, len(entity_list)):
                name_b, eps_b = entity_list[j]
                shared = set(eps_a) & set(eps_b)
                if shared:
                    id_a = f"entity:{name_a}" if f"entity:{name_a}" in entity_nodes else f"web3_entity:{name_a}"
                    id_b = f"entity:{name_b}" if f"entity:{name_b}" in entity_nodes else f"web3_entity:{name_b}"
                    pair = tuple(sorted([id_a, id_b]))
                    if pair not in entity_pairs_seen:
                        entity_pairs_seen.add(pair)
                        edges.append({
                            "from": pair[0],
                            "to": pair[1],
                            "relationship": "shared_context",
                        })

        # Signal → Entity: relevance (entity triggers signal)
        for entity_name, signal_type in ENTITY_SIGNAL_MAP.items():
            eid = f"entity:{entity_name}"
            we3id = f"web3_entity:{entity_name}"
            sid = f"signal:{signal_type}"
            if eid in entity_nodes and sid in signal_nodes:
                edges.append({
                    "from": eid,
                    "to": sid,
                    "relationship": "triggers",
                })
            if we3id in web3_nodes and sid in signal_nodes:
                edges.append({
                    "from": we3id,
                    "to": sid,
                    "relationship": "triggers",
                })

        # Endpoint → Endpoint: shared entity bridge
        ep_pairs_seen: Set[Tuple[str, str]] = set()
        for entity_name, ep_ids in entity_endpoints.items():
            unique_eps = sorted(set(ep_ids))
            for i, eid_a in enumerate(unique_eps):
                for j in range(i + 1, len(unique_eps)):
                    eid_b = unique_eps[j]
                    if eid_a in endpoint_nodes and eid_b in endpoint_nodes:
                        pair = tuple(sorted([eid_a, eid_b]))
                        if pair not in ep_pairs_seen:
                            ep_pairs_seen.add(pair)
                            edges.append({
                                "from": pair[0],
                                "to": pair[1],
                                "relationship": "shares_entity",
                            })

        return edges


class ClusterEngine:
    """
    Groups endpoints into investigation clusters based on shared signals,
    labels, attack surfaces, and entity types.
    """

    def build(
        self, scored_endpoints: List[Dict[str, Any]], entity_endpoints: Dict[str, List[str]]
    ) -> List[Cluster]:
        clusters: List[Cluster] = []
        endpoint_map = {
            f"endpoint:{e.get('method','GET')}:{e.get('path','/')}": e
            for e in scored_endpoints
        }

        for definition in CLUSTER_DEFINITIONS:
            name = definition["name"]
            matched: List[Dict[str, Any]] = []
            reasons: List[str] = []

            for ep in scored_endpoints:
                eid = f"endpoint:{ep.get('method','GET')}:{ep.get('path','/')}"
                labels = ep.get("labels", [])
                surfaces = ep.get("attack_surface", [])
                signals = ep.get("signals", [])
                lower_path = str(ep.get("path", "")).lower()

                in_cluster = False

                for label in definition["labels"]:
                    if label in labels:
                        in_cluster = True
                        break

                if not in_cluster:
                    for surface in definition["surfaces"]:
                        if surface in surfaces:
                            in_cluster = True
                            break

                if not in_cluster:
                    for signal in definition["signals"]:
                        if signal in signals:
                            in_cluster = True
                            break

                if not in_cluster:
                    for entity in definition["entities"]:
                        patterns = ENTITY_PATTERNS.get(entity, [entity])
                        if any(f"/{p}" in lower_path or lower_path.startswith(f"{p}/") for p in patterns):
                            in_cluster = True
                            break

                if in_cluster:
                    matched.append(ep)
                    matched_reasons = []
                    for label in definition["labels"]:
                        if label in labels:
                            matched_reasons.append(f"label:{label}")
                    for surface in definition["surfaces"]:
                        if surface in surfaces:
                            matched_reasons.append(f"surface:{surface}")
                    for signal in definition["signals"]:
                        if signal in signals:
                            matched_reasons.append(f"signal:{signal}")
                    for entity in definition["entities"]:
                        patterns = ENTITY_PATTERNS.get(entity, [entity])
                        if any(f"/{p}" in lower_path for p in patterns):
                            matched_reasons.append(f"entity:{entity}")
                    if matched_reasons:
                        reasons.append(f"{ep.get('method','GET')} {ep.get('path','/')} ({', '.join(matched_reasons)})")

            # Confidence: ratio of endpoints with direct matches vs. entity-only
            direct_matches = 0
            for ep in matched:
                labels = ep.get("labels", [])
                surfaces = ep.get("attack_surface", [])
                signals = ep.get("signals", [])
                has_direct = (
                    any(l in definition["labels"] for l in labels)
                    or any(s in definition["surfaces"] for s in surfaces)
                    or any(s in definition["signals"] for s in signals)
                )
                if has_direct:
                    direct_matches += 1

            confidence = round(direct_matches / len(matched), 2) if matched else 0.0

            clusters.append(Cluster(
                name=name,
                endpoints=matched,
                confidence=confidence,
                reasoning=reasons,
            ))

        return clusters


class HotPathDetector:
    """
    Generates prioritized investigation paths by connecting clusters
    through shared entities.
    """

    def detect(
        self,
        clusters: List[Cluster],
        scored_endpoints: List[Dict[str, Any]],
        entity_endpoints: Dict[str, List[str]],
    ) -> List[HotPath]:
        cluster_map: Dict[str, Cluster] = {c.name: c for c in clusters}
        hot_paths: List[HotPath] = []
        seen: Set[str] = set()

        for template in HOT_PATH_TEMPLATES:
            start = cluster_map.get(template["start_cluster"])
            end = cluster_map.get(template["end_cluster"])
            bridge_entity = template["bridge_entity"]

            if not start or not end:
                continue
            if not start.endpoints or not end.endpoints:
                continue

            path_key = f"{template['start_cluster']}->{bridge_entity}->{template['end_cluster']}"
            if path_key in seen:
                continue
            seen.add(path_key)

            # Find endpoints in start cluster that reference the bridge entity
            start_with_entity = []
            for ep in start.endpoints:
                eid = f"endpoint:{ep.get('method','GET')}:{ep.get('path','/')}"
                if eid in entity_endpoints.get(bridge_entity, []):
                    start_with_entity.append(ep)

            # Find endpoints in end cluster that reference the bridge entity
            end_with_entity = []
            for ep in end.endpoints:
                eid = f"endpoint:{ep.get('method','GET')}:{ep.get('path','/')}"
                if eid in entity_endpoints.get(bridge_entity, []):
                    end_with_entity.append(ep)

            # If either side lacks the bridge, try relaxing: any endpoint in the cluster
            path_nodes: List[str] = []
            if start_with_entity:
                best = max(start_with_entity, key=lambda x: float(x.get("risk_score", 0)))
                path_nodes.append(f"endpoint:{best.get('method','GET')}:{best.get('path','/')}")
            elif start.endpoints:
                best = max(start.endpoints, key=lambda x: float(x.get("risk_score", 0)))
                path_nodes.append(f"endpoint:{best.get('method','GET')}:{best.get('path','/')}")
            else:
                continue

            path_nodes.append(f"entity:{bridge_entity}")

            if end_with_entity:
                best = max(end_with_entity, key=lambda x: float(x.get("risk_score", 0)))
                path_nodes.append(f"endpoint:{best.get('method','GET')}:{best.get('path','/')}")
            elif end.endpoints:
                best = max(end.endpoints, key=lambda x: float(x.get("risk_score", 0)))
                path_nodes.append(f"endpoint:{best.get('method','GET')}:{best.get('path','/')}")
            else:
                continue

            why = template["template"].format(**{bridge_entity: bridge_entity})

            # Upgrade reward if billing/admin involved
            reward = template["reward"]
            scoring_check = start_with_entity + end_with_entity
            if scoring_check:
                avg_score = sum(float(e.get("risk_score", 0)) for e in scoring_check) / len(scoring_check)
                if avg_score >= 80:
                    reward = "high"
                elif avg_score >= 50:
                    if reward == "low":
                        reward = "medium"

            hot_paths.append(HotPath(
                nodes=path_nodes,
                why_it_matters=why,
                estimated_reward=reward,
            ))

        # Reward-sort: high first, then medium, then low
        reward_order = {"high": 0, "medium": 1, "low": 2}
        hot_paths.sort(key=lambda p: reward_order.get(p.estimated_reward, 99))

        return hot_paths


class InvestigationGraphBuilder:
    """
    Main orchestrator.

    Transforms scored endpoints into an investigation graph with:
      - nodes (endpoints, entities, signals)
      - edges (relationships)
      - clusters (logical groups)
      - hot paths (prioritized investigation routes)
    """

    def __init__(self):
        self.node_extractor = NodeExtractor()
        self.relationship_detector = RelationshipDetector()
        self.cluster_engine = ClusterEngine()
        self.hot_path_detector = HotPathDetector()

    def build(
        self,
        scored_endpoints: List[Dict[str, Any]],
    ) -> InvestigationReport:
        if not scored_endpoints:
            return InvestigationReport(
                graph={"nodes": [], "edges": []},
                clusters=[],
                hot_paths=[],
            )

        nodes, entity_endpoints = self.node_extractor.extract(scored_endpoints)
        edges = self.relationship_detector.detect(nodes, scored_endpoints, entity_endpoints)
        clusters = self.cluster_engine.build(scored_endpoints, entity_endpoints)
        hot_paths = self.hot_path_detector.detect(clusters, scored_endpoints, entity_endpoints)

        return InvestigationReport(
            graph={"nodes": nodes, "edges": edges},
            clusters=clusters,
            hot_paths=hot_paths,
        )
