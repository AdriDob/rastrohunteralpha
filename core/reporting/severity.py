from typing import Dict, Optional, Tuple

SEVERITY_LEVELS = ["critical", "high", "medium", "low", "info"]

SEVERITY_THRESHOLDS: Dict[str, Tuple[float, float]] = {
    "critical": (85.0, 100.0),
    "high": (65.0, 84.9),
    "medium": (40.0, 64.9),
    "low": (15.0, 39.9),
    "info": (0.0, 14.9),
}


def risk_to_severity(risk_score: float) -> str:
    for level, (lo, hi) in SEVERITY_THRESHOLDS.items():
        if lo <= risk_score <= hi:
            return level
    return "info"


def confidence_to_label(confidence: float) -> str:
    if confidence >= 0.8:
        return "confirmed"
    if confidence >= 0.6:
        return "likely"
    if confidence >= 0.3:
        return "possible"
    return "unlikely"


def severity_score(severity: str) -> float:
    mapping = {
        "critical": 10.0,
        "high": 7.5,
        "medium": 5.0,
        "low": 2.5,
        "info": 0.0,
    }
    return mapping.get(severity, 0.0)


def parse_cvss_vector(vector: Optional[str]) -> tuple:
    """Parse a CVSS vector string and return (numeric_score, severity_label).

    Tries CVSS 3.x, 2.0, and 4.0 in order.
    Returns (0.0, "None") for missing or unparseable vectors.
    """
    if not vector:
        return (0.0, "None")
    try:
        from cvss import CVSS2, CVSS3, CVSS4
    except ImportError:
        return (0.0, "None")

    for cls in (CVSS3, CVSS2, CVSS4):
        try:
            obj = cls(vector)
            return (obj.scores()[0], obj.severities()[0])
        except Exception:
            continue
    return (0.0, "None")


def cvss_vector(risk_score: float, is_authenticated: bool = False) -> str:
    severity = risk_to_severity(risk_score)
    av = "N"  # Network
    ac = "L"  # Low
    if severity == "critical":
        pr = "N" if not is_authenticated else "L"
        ui = "N"
        s = "C"
        c = "H"
        i = "H"
        a = "H"
    elif severity == "high":
        pr = "L" if not is_authenticated else "H"
        ui = "N"
        s = "C"
        c = "H"
        i = "H"
        a = "N"
    elif severity == "medium":
        pr = "L"
        ui = "R"
        s = "U"
        c = "L"
        i = "L"
        a = "N"
    else:
        pr = "H"
        ui = "R"
        s = "U"
        c = "N"
        i = "N"
        a = "N"
    return f"CVSS:3.1/AV:{av}/AC:{ac}/PR:{pr}/UI:{ui}/S:{s}/C:{c}/I:{i}/A:{a}"
