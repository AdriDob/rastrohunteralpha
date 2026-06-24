import json
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

LOG = logging.getLogger("rastro.recon.burp")


@dataclass
class BurpItem:
    url: str
    host: str
    port: int
    protocol: str
    method: str
    path: str
    status: int
    length: int
    mime_type: str
    request: str = ""
    response: str = ""
    comment: str = ""
    findings: Dict[str, Any] = field(default_factory=dict)


def parse_burp_xml(path: Path) -> List[BurpItem]:
    """Parse Burp Suite XML export into structured items."""
    items = []
    try:
        tree = ET.parse(path)
        root = tree.getroot()
    except ET.ParseError as e:
        LOG.error("Failed to parse Burp XML %s: %s", path, e)
        return []

    for item in root.iter("item"):
        try:
            url_el = item.find("url")
            url = url_el.text if url_el is not None else ""

            host_el = item.find("host")
            host_text = host_el.text if host_el is not None else ""
            ip = host_el.get("ip", "") if host_el is not None else ""

            port_el = item.find("port")
            port = int(port_el.text) if port_el is not None else 0

            protocol_el = item.find("protocol")
            protocol = protocol_el.text if protocol_el is not None else "http"

            method_el = item.find("method")
            method = method_el.text if method_el is not None else "GET"

            path_el = item.find("path")
            path_text = path_el.text if path_el is not None else ""

            status_el = item.find("status")
            status = int(status_el.text) if status_el is not None else 0

            length_el = item.find("length")
            length = int(length_el.text) if length_el is not None else 0

            mime_el = item.find("mimetype")
            mime = mime_el.text if mime_el is not None else ""

            req_el = item.find("request")
            request = req_el.text if req_el is not None else ""

            resp_el = item.find("response")
            response = resp_el.text if resp_el is not None else ""

            comment_el = item.find("comment")
            comment = comment_el.text if comment_el is not None else ""

            burp_item = BurpItem(
                url=url,
                host=host_text,
                port=port,
                protocol=protocol,
                method=method,
                path=path_text,
                status=status,
                length=length,
                mime_type=mime,
                request=request,
                response=response,
                comment=comment,
            )

            burp_item.findings = _analyze_burp_item(burp_item)
            items.append(burp_item)

        except (AttributeError, ValueError, TypeError) as e:
            LOG.warning("Skipping malformed Burp item: %s", e)
            continue

    LOG.info("Parsed %d items from Burp XML %s", len(items), path)
    return items


def parse_burp_json(path: Path) -> List[BurpItem]:
    """Parse Burp Suite JSON export."""
    items = []
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        LOG.error("Failed to parse Burp JSON %s: %s", path, e)
        return []

    raw_list = data if isinstance(data, list) else data.get("items", data.get("messages", []))

    for entry in raw_list:
        try:
            url = entry.get("url", "")
            host = entry.get("host", "")
            port = entry.get("port", 0)
            protocol = entry.get("protocol", "http")
            method = entry.get("method", "GET")
            path_text = entry.get("path", "")
            status = entry.get("status", 0)
            length = entry.get("length", 0)
            mime = entry.get("mimeType", entry.get("mime_type", ""))
            request = entry.get("request", "")
            response = entry.get("response", "")
            comment = entry.get("comment", "")

            burp_item = BurpItem(
                url=url, host=host, port=port, protocol=protocol,
                method=method, path=path_text, status=status,
                length=length, mime_type=mime, request=request,
                response=response, comment=comment,
            )
            burp_item.findings = _analyze_burp_item(burp_item)
            items.append(burp_item)

        except (AttributeError, TypeError, ValueError) as e:
            LOG.warning("Skipping malformed JSON entry: %s", e)

    LOG.info("Parsed %d items from Burp JSON %s", len(items), path)
    return items


def _analyze_burp_item(item: BurpItem) -> Dict[str, Any]:
    """Analyze a single Burp item for interesting findings."""
    findings: Dict[str, Any] = {}
    flags = []

    if item.status == 200:
        if any(kw in item.url for kw in ["admin", "login", "dashboard", "panel"]):
            flags.append("admin_panel")
        if any(kw in item.url for kw in ["api", "v1", "v2", "graphql", "rest"]):
            flags.append("api_endpoint")
        if any(item.path.endswith(ext) for ext in [".bak", ".zip", ".tar", ".gz", ".sql", ".env"]):
            flags.append("potential_backup")

    if item.status in (301, 302, 307, 308):
        flags.append("redirect")

    if item.status == 403:
        flags.append("forbidden")
    elif item.status == 401:
        flags.append("unauthorized")
    elif item.status == 500:
        flags.append("server_error")

    findings["flags"] = flags
    findings["severity"] = "info"
    if any(f in flags for f in ["admin_panel", "potential_backup"]):
        findings["severity"] = "medium"
    elif "api_endpoint" in flags:
        findings["severity"] = "low"

    return findings


def import_burp(path: Path) -> List[BurpItem]:
    """Auto-detect format and import Burp Suite data."""
    if not path.exists():
        LOG.error("Burp import file not found: %s", path)
        return []

    ext = path.suffix.lower()
    if ext == ".xml":
        return parse_burp_xml(path)
    elif ext == ".json":
        return parse_burp_json(path)
    else:
        LOG.warning("Unknown Burp file format: %s. Trying XML.", ext)
        return parse_burp_xml(path)
