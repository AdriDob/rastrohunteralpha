import json
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

LOG = logging.getLogger("rastro.recon.zap")


@dataclass
class ZapAlert:
    alert: str
    risk: str
    confidence: str
    url: str
    param: str
    attack: str
    description: str
    solution: str
    reference: str
    cwe_id: str = ""
    wasc_id: str = ""
    plugin_id: str = ""


@dataclass
class ZapSite:
    name: str
    urls: list[str] = field(default_factory=list)
    alerts: list[ZapAlert] = field(default_factory=list)


def parse_zap_xml(path: Path) -> list[ZapSite]:
    """Parse OWASP ZAP XML report into structured alerts."""
    sites_map: dict[str, ZapSite] = {}

    try:
        tree = ET.parse(path)
        root = tree.getroot()
    except ET.ParseError as e:
        LOG.error("Failed to parse ZAP XML %s: %s", path, e)
        return []


    for alertitem in root.iter("alertitem"):
        try:
            alert_name_el = alertitem.find("alert")
            alert_name = alert_name_el.text if alert_name_el is not None else ""

            risk_el = alertitem.find("risk")
            risk = risk_el.text if risk_el is not None else "Unknown"

            confidence_el = alertitem.find("confidence")
            confidence = confidence_el.text if confidence_el is not None else "Unknown"

            url_el = alertitem.find("url")
            url = url_el.text if url_el is not None else ""

            param_el = alertitem.find("param")
            param = param_el.text if param_el is not None else ""

            attack_el = alertitem.find("attack")
            attack = attack_el.text if attack_el is not None else ""

            desc_el = alertitem.find("description")
            description = desc_el.text if desc_el is not None else ""

            solution_el = alertitem.find("solution")
            solution = solution_el.text if solution_el is not None else ""

            ref_el = alertitem.find("reference")
            reference = ref_el.text if ref_el is not None else ""

            cwe_el = alertitem.find("cweid")
            cwe_id = cwe_el.text if cwe_el is not None else ""

            wasc_el = alertitem.find("wascid")
            wasc_id = wasc_el.text if wasc_el is not None else ""

            plugin_el = alertitem.find("pluginid")
            plugin_id = plugin_el.text if plugin_el is not None else ""

            alert = ZapAlert(
                alert=alert_name,
                risk=risk,
                confidence=confidence,
                url=url,
                param=param,
                attack=attack,
                description=description,
                solution=solution,
                reference=reference,
                cwe_id=cwe_id,
                wasc_id=wasc_id,
                plugin_id=plugin_id,
            )

            # Extract site name from URL
            from urllib.parse import urlparse
            parsed = urlparse(url)
            site_name = f"{parsed.scheme}://{parsed.netloc}"

            if site_name not in sites_map:
                sites_map[site_name] = ZapSite(name=site_name)
            sites_map[site_name].alerts.append(alert)
            if url not in sites_map[site_name].urls:
                sites_map[site_name].urls.append(url)

        except (AttributeError, ValueError, TypeError) as e:
            LOG.warning("Skipping malformed ZAP alert: %s", e)
            continue

    sites = list(sites_map.values())
    LOG.info("Parsed %d sites with %d total alerts from ZAP XML %s",
             len(sites), sum(len(s.urls) for s in sites), path)
    return sites


def parse_zap_json(path: Path) -> list[ZapSite]:
    """Parse OWASP ZAP JSON report."""
    sites_map: dict[str, ZapSite] = {}

    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        LOG.error("Failed to parse ZAP JSON %s: %s", path, e)
        return []

    site_list = data if isinstance(data, list) else data.get("site", [])

    for site_entry in site_list:
        site_name = site_entry.get("@name", "")
        if not site_name:
            continue

        site = sites_map.setdefault(site_name, ZapSite(name=site_name))
        alert_items = site_entry.get("alerts", []) if isinstance(site_entry, dict) else []

        for alert_item in alert_items:
            if not isinstance(alert_item, dict):
                continue
            try:
                alert = ZapAlert(
                    alert=alert_item.get("alert", alert_item.get("name", "")),
                    risk=alert_item.get("risk", alert_item.get("riskdesc", "Unknown")),
                    confidence=alert_item.get("confidence", "Unknown"),
                    url=alert_item.get("url", ""),
                    param=alert_item.get("param", ""),
                    attack=alert_item.get("attack", ""),
                    description=alert_item.get("description", ""),
                    solution=alert_item.get("solution", ""),
                    reference=alert_item.get("reference", ""),
                    cwe_id=str(alert_item.get("cweid", "")),
                    wasc_id=str(alert_item.get("wascid", "")),
                    plugin_id=str(alert_item.get("pluginid", "")),
                )
                site.alerts.append(alert)
                if alert.url and alert.url not in site.urls:
                    site.urls.append(alert.url)
            except (AttributeError, TypeError, ValueError) as e:
                LOG.warning("Skipping malformed ZAP JSON alert: %s", e)

    sites = list(sites_map.values())
    LOG.info("Parsed %d sites with %d alerts from ZAP JSON %s",
             len(sites), sum(len(s.alerts) for s in sites), path)
    return sites


def import_zap(path: Path) -> list[ZapSite]:
    """Auto-detect format and import OWASP ZAP report."""
    if not path.exists():
        LOG.error("ZAP import file not found: %s", path)
        return []

    ext = path.suffix.lower()
    if ext == ".xml":
        return parse_zap_xml(path)
    elif ext == ".json":
        return parse_zap_json(path)
    else:
        LOG.warning("Unknown ZAP file format: %s. Trying XML.", ext)
        return parse_zap_xml(path)


def risk_score(risk: str) -> int:
    """Convert ZAP risk level to numeric score."""
    mapping = {"high": 3, "medium": 2, "low": 1, "info": 0, "informational": 0}
    return mapping.get(risk.lower(), 0)


def filter_high_risk(sites: list[ZapSite], min_risk: str = "medium") -> list[ZapSite]:
    """Filter alerts by minimum risk level."""
    min_score = risk_score(min_risk)
    filtered = []
    for site in sites:
        filtered_alerts = [a for a in site.alerts if risk_score(a.risk) >= min_score]
        if filtered_alerts:
            filtered.append(ZapSite(name=site.name, urls=site.urls, alerts=filtered_alerts))
    return filtered
