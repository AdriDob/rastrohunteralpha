"""
hypothesis.llm — LLM integration for hypothesis reasoning and prioritization.

The LLM is used ONLY for:
1. Reasoning enrichment — given existing rule-based hypotheses, the LLM adds
   context, attack narratives, and edge cases.
2. Priority refinement — the LLM reviews the top-K hypotheses and suggests
   reordering based on subtle contextual signals.
3. Gap detection — given endpoints that produced no hypotheses, the LLM
   checks for missed vulnerability patterns.

The LLM is NEVER used for scanning, recon, or primary scoring.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from core_engines.engine.hypothesis.models import Hypothesis

LOG = logging.getLogger("rastro.hypothesis.llm")


REASONING_PROMPT = """You are a senior bug bounty hunter reviewing automated vulnerability hypotheses.

For each hypothesis below, your task is to:
1. Rate the hypothesis from 1-10 (10 = most promising) based on the signals present
2. Add a concise, specific attack narrative (1-2 sentences)
3. Suggest ONE edge case or advanced technique the rule-based generator missed

Output format: JSON array of objects with fields:
  - id: string (matching the hypothesis id)
  - priority_rating: int 1-10
  - attack_narrative: string
  - edge_case: string

Hypotheses:
{hypotheses_json}

Rules:
- Be concise and specific. No general advice.
- Focus on subtle signals the rules might miss (e.g., unusual parameter combinations, deprecated API versions, chained vulnerabilities).
- If a hypothesis has strong signals, rate it 8+. If signals are weak, rate it 2-4.
- Never suggest scanning or brute-forcing. Only reasoning.
- Output ONLY valid JSON, no markdown, no explanation.
"""

GAP_ANALYSIS_PROMPT = """You are a senior bug bounty hunter reviewing endpoints that did NOT trigger any automated hypothesis.

For the following endpoints, determine if there are any vulnerability types the rule-based engine might have missed.

Endpoint data:
{endpoints_json}

Output format: JSON array of objects with fields:
  - endpoint_path: string
  - vulnerability_type: string (idor, ssrf, auth_bypass, xss, sqli, graphql_introspection, privilege_escalation, data_exposure, rate_limit_bypass, business_logic, file_operation, ssti, web3_signature_replay, web3_rpc_leak)
  - reason_missed: string (why the rule engine missed this)
  - suggested_test: string (specific test to run)
  - confidence: float 0.0-1.0

Output ONLY valid JSON, no markdown, no explanation.
"""

PRIORITY_PROMPT = """You are a senior bug bounty hunter prioritizing vulnerability hypotheses for manual testing.

Given these hypotheses sorted by automated priority score, determine if the order should change based on:
- Industry-wide commonality of each vulnerability type in current programs
- Signal strength relative to other hypotheses
- Potential for chained vulnerabilities between hypotheses

Hypotheses (sorted by current priority):
{hypotheses_json}

Output: JSON object with:
  - reorder_suggestions: list of hypothesis IDs in new priority order (top 5 only)
  - reasoning: string explaining the reorder

Output ONLY valid JSON, no markdown, no explanation.
"""


def _build_ollama_payload(model: str, prompt: str, max_tokens: int = 512) -> dict[str, Any]:
    return {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "max_tokens": max_tokens,
            "stop": ["```", "\n\n\n"],
        },
    }


def _call_ollama(prompt: str, host: str = "http://localhost:11434", model: str = "qwen2.5-coder") -> str | None:
    import urllib.error
    import urllib.request

    payload = _build_ollama_payload(model, prompt)
    try:
        req = urllib.request.Request(
            f"{host}/api/generate",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = resp.read().decode()
            data = json.loads(result)
            return data.get("response", "")
    except (urllib.error.URLError, json.JSONDecodeError, ConnectionRefusedError, TimeoutError) as e:
        LOG.warning("Ollama call failed (hypothesis LLM): %s", e)
        return None


def _parse_json_response(text: str | None) -> Any | None:
    if not text:
        return None
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0]
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        LOG.warning("Failed to decode JSON response from LLM", exc_info=True)
    import re
    match = re.search(r"(\[.*?\]|\{.*\})", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            LOG.warning("Failed to extract JSON from LLM response via regex", exc_info=True)
    return None


def enrich_reasoning(
    hypotheses: list[Hypothesis],
    ollama_host: str = "http://localhost:11434",
    model: str = "qwen2.5-coder",
) -> list[Hypothesis]:
    if not hypotheses:
        return hypotheses

    hyps_data = [
        {
            "id": h.id,
            "vulnerability_type": h.vulnerability_type.value,
            "endpoint_path": h.endpoint.get("path", ""),
            "method": h.endpoint.get("method", "GET"),
            "risk_score": h.endpoint.get("risk_score", 0),
            "signals": h.endpoint.get("signals", []),
            "evidence": h.evidence[:3],
            "current_priority": h.priority_score,
        }
        for h in hypotheses[:15]
    ]

    prompt = REASONING_PROMPT.format(hypotheses_json=json.dumps(hyps_data, indent=2))
    response = _call_ollama(prompt, host=ollama_host, model=model)
    parsed = _parse_json_response(response)

    if not isinstance(parsed, list):
        LOG.info("LLM reasoning enrichment returned no usable data")
        return hypotheses

    enrichment_map = {}
    for item in parsed:
        if isinstance(item, dict) and "id" in item:
            enrichment_map[item["id"]] = item

    enriched = []
    for h in hypotheses:
        enrichment = enrichment_map.get(h.id)
        if enrichment and isinstance(enrichment, dict):
            narrative = enrichment.get("attack_narrative", "")
            edge_case = enrichment.get("edge_case", "")
            combined_reasoning = h.reasoning
            if narrative:
                combined_reasoning += f" | LLM: {narrative}"
            if edge_case:
                combined_reasoning += f" | Edge: {edge_case}"

            priority_rating = enrichment.get("priority_rating")
            priority_boost = 0.0
            if isinstance(priority_rating, (int, float)):
                priority_boost = (priority_rating - 5) * 0.5

            enriched.append(Hypothesis(
                id=h.id,
                vulnerability_type=h.vulnerability_type,
                target_id=h.target_id,
                target_name=h.target_name,
                endpoint=h.endpoint,
                likelihood=min(max(h.likelihood + 0.02 * (priority_boost / 2), 0.05), 0.95),
                impact=h.impact,
                exploitability=h.exploitability,
                confidence=h.confidence,
                priority_score=max(h.priority_score + priority_boost, 0),
                evidence=h.evidence,
                reasoning=combined_reasoning,
                suggested_actions=h.suggested_actions + ([f"Edge case: {edge_case}"] if edge_case else []),
                source=h.source,
                vector=h.vector,
                attack_surface_labels=h.attack_surface_labels,
                similarity_to_past=h.similarity_to_past,
                past_pattern_id=h.past_pattern_id,
                score=h.score,
            ))
        else:
            enriched.append(h)

    return enriched


def detect_gaps(
    all_endpoints: list[dict[str, Any]],
    hypotheses: list[Hypothesis],
    ollama_host: str = "http://localhost:11434",
    model: str = "qwen2.5-coder",
) -> list[dict[str, Any]]:
    hypothesis_endpoint_ids = {h.endpoint.get("id") for h in hypotheses if h.endpoint.get("id")}
    missed = [ep for ep in all_endpoints if ep.get("id") not in hypothesis_endpoint_ids]

    if not missed:
        return []

    gap_data = [
        {
            "endpoint_path": ep.get("path", ""),
            "method": ep.get("method", "GET"),
            "risk_score": ep.get("risk_score", 0),
            "signals": ep.get("signals", []),
            "labels": ep.get("labels", []),
        }
        for ep in missed[:20]
    ]

    prompt = GAP_ANALYSIS_PROMPT.format(endpoints_json=json.dumps(gap_data, indent=2))
    response = _call_ollama(prompt, host=ollama_host, model=model)
    parsed = _parse_json_response(response)

    if not isinstance(parsed, list):
        return []

    return [item for item in parsed if isinstance(item, dict)]


def refine_priority(
    hypotheses: list[Hypothesis],
    ollama_host: str = "http://localhost:11434",
    model: str = "qwen2.5-coder",
) -> list[str] | None:
    if len(hypotheses) < 3:
        return None

    hyps_data = [
        {
            "id": h.id,
            "vulnerability_type": h.vulnerability_type.value,
            "endpoint_path": h.endpoint.get("path", ""),
            "risk_score": h.endpoint.get("risk_score", 0),
            "priority_score": h.priority_score,
            "evidence": h.evidence[:2],
        }
        for h in hypotheses[:10]
    ]

    prompt = PRIORITY_PROMPT.format(hypotheses_json=json.dumps(hyps_data, indent=2))
    response = _call_ollama(prompt, host=ollama_host, model=model)
    parsed = _parse_json_response(response)

    if isinstance(parsed, dict) and "reorder_suggestions" in parsed:
        suggestions = parsed["reorder_suggestions"]
        if isinstance(suggestions, list) and suggestions:
            return suggestions
    return None
