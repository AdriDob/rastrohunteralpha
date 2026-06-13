import csv
import io
import json
from typing import Any, Dict, List


def to_json(data: Any, indent: int = 2) -> str:
    return json.dumps(data, indent=indent, default=str)


def to_markdown_table(headers: List[str], rows: List[List[str]]) -> str:
    buf = io.StringIO()
    buf.write(" | ".join(headers) + "\n")
    buf.write(" | ".join("---" for _ in headers) + "\n")
    for row in rows:
        buf.write(" | ".join(row) + "\n")
    return buf.getvalue()


def to_csv(headers: List[str], rows: List[List[str]]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    writer.writerows(rows)
    return buf.getvalue()


def export_findings(findings: List[Dict[str, Any]], fmt: str = "json") -> str:
    headers = ["id", "title", "severity", "target_name", "endpoint_path", "payout", "description"]
    rows = []
    for f in findings:
        rows.append([
            str(f.get("id", "")),
            str(f.get("title", "")),
            str(f.get("severity", "")),
            str(f.get("target_name", "")),
            str(f.get("endpoint_path", "") or ""),
            str(f.get("payout", 0)),
            str(f.get("description", "") or ""),
        ])
    if fmt == "csv":
        return to_csv(headers, rows)
    if fmt == "markdown":
        return to_markdown_table(headers, rows)
    return to_json(findings)
