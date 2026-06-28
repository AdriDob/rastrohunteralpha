import csv
import io
from typing import Any


def _to_csv(headers: list[str], rows: list[list[str]]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    writer.writerows(rows)
    return buf.getvalue()


def _to_markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    buf = io.StringIO()
    buf.write(" | ".join(headers) + "\n")
    buf.write(" | ".join("---" for _ in headers) + "\n")
    for row in rows:
        buf.write(" | ".join(row) + "\n")
    return buf.getvalue()


def export_history(history: Any, fmt: str) -> str:
    d = history.to_dict() if hasattr(history, 'to_dict') else history
    if fmt == "csv":
        headers = ["metric", "value"]
        rows = []
        for k, v in d.items():
            if isinstance(v, (int, float, str)):
                rows.append([str(k), str(v)])
            elif isinstance(v, list):
                rows.append([str(k), str(len(v)) + " items"])
            elif isinstance(v, dict):
                for sk, sv in v.items():
                    rows.append([f"{k}.{sk}", str(sv)])
        return _to_csv(headers, rows)
    if fmt == "markdown":
        buf = io.StringIO()
        buf.write("# Historical Summary\n\n")
        for k, v in d.items():
            if isinstance(v, (int, float, str)):
                buf.write(f"- **{k}**: {v}\n")
            elif isinstance(v, list):
                buf.write(f"- **{k}**: {len(v)} items\n")
        buf.write("\n## Top Vulnerability Types\n\n")
        for vt in d.get("top_vulnerability_types", []):
            if isinstance(vt, dict):
                buf.write(f"- {vt.get('vulnerability_type', '?')}: {vt.get('total_count', 0)} occurrences, "
                          f"{vt.get('acceptance_rate', 0):.0%} acceptance\n")
        return buf.getvalue()
    return str(d)


def export_trends(trends: Any, fmt: str) -> str:
    d = trends.to_dict() if hasattr(trends, 'to_dict') else trends
    if fmt == "csv":
        headers = ["trend_type", "label", "direction", "current_value", "confidence", "sample_size"]
        rows = []
        for category in ["rising_surfaces", "emerging_vulnerability_classes",
                          "growing_target_categories", "repeated_endpoint_patterns"]:
            for signal in d.get(category, []):
                rows.append([
                    category,
                    signal.get("label", ""),
                    signal.get("direction", ""),
                    str(signal.get("current_value", "")),
                    str(signal.get("confidence", "")),
                    str(signal.get("sample_size", "")),
                ])
        return _to_csv(headers, rows)
    if fmt == "markdown":
        buf = io.StringIO()
        buf.write("# Trend Report\n\n")
        for category in ["rising_surfaces", "emerging_vulnerability_classes",
                          "growing_target_categories", "repeated_endpoint_patterns"]:
            items = d.get(category, [])
            if not items:
                continue
            buf.write(f"## {category.replace('_', ' ').title()}\n\n")
            for signal in items:
                buf.write(f"- **{signal.get('label', '?')}**: {signal.get('current_value', 0)} "
                          f"(confidence: {signal.get('confidence', 0):.0%})\n")
            buf.write("\n")
        return buf.getvalue()
    return str(d)


def export_recommendations(recs: Any, fmt: str) -> str:
    d = recs.to_dict() if hasattr(recs, 'to_dict') else recs
    if fmt == "csv":
        rows = []
        for rec_type, items in [("target", d.get("targets", [])),
                                  ("surface", d.get("surfaces", [])),
                                  ("quick_win", d.get("quick_wins", [])),
                                  ("report", d.get("reports", []))]:
            for item in items:
                rows.append([rec_type, str(item)])
        return _to_csv(["type", "detail"], rows)
    if fmt == "markdown":
        buf = io.StringIO()
        buf.write("# Recommendations\n\n")
        for section, label in [("targets", "Target Recommendations"),
                                ("surfaces", "Surface Recommendations"),
                                ("quick_wins", "Quick Win Recommendations"),
                                ("reports", "Report Recommendations")]:
            items = d.get(section, [])
            if not items:
                continue
            buf.write(f"## {label}\n\n")
            for item in items:
                score = item.get("priority_score") or item.get("quick_win_score") or item.get("acceptance_probability") or 0
                name = item.get("target_name") or item.get("surface") or item.get("title") or "?"
                reason = item.get("reason", "")
                buf.write(f"- **{name}** (score: {score}): {reason}\n")
            buf.write("\n")
        return buf.getvalue()
    return str(d)


def export_snapshots(snapshots: list[dict[str, Any]], fmt: str) -> str:
    if fmt == "csv":
        headers = ["id", "key", "snapshot_type", "targets", "endpoints", "findings",
                    "confirmed", "payout", "acceptance_rate", "created_at"]
        rows = []
        for snap in snapshots:
            d = snap.get("details", {})
            rows.append([
                str(snap.get("id", "")),
                snap.get("key", ""),
                d.get("snapshot_type", ""),
                str(d.get("total_targets", "")),
                str(d.get("total_endpoints", "")),
                str(d.get("total_findings", "")),
                str(d.get("confirmed_verdicts", "")),
                str(d.get("total_payout", "")),
                f'{d.get("acceptance_rate", 0):.0%}',
                snap.get("created_at", ""),
            ])
        return _to_csv(headers, rows)
    if fmt == "markdown":
        buf = io.StringIO()
        buf.write("# Learning Snapshots\n\n")
        for snap in snapshots:
            d = snap.get("details", {})
            buf.write(f"### {snap.get('key', '?')}\n\n")
            for k in ["total_targets", "total_endpoints", "total_findings",
                       "confirmed_verdicts", "total_payout", "acceptance_rate"]:
                buf.write(f"- **{k}**: {d.get(k, '')}\n")
            buf.write("\n")
        return buf.getvalue()
    return str(snapshots)
