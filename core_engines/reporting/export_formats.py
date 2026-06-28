import json
from pathlib import Path

try:
    from jinja2 import Environment, FileSystemLoader
except ImportError:
    Environment = None


class ExportFormats:
    def __init__(self):
        self._jinja_env = None
        if Environment is not None:
            tmpl_dir = Path(__file__).resolve().parent / "templates"
            if tmpl_dir.is_dir():
                self._jinja_env = Environment(
                    loader=FileSystemLoader(str(tmpl_dir)),
                    autoescape=True,
                )

    def generate_all(
        self,
        title: str,
        narrative: str,
        severity: str,
        cvss: str,
        affected_endpoint: str,
        affected_method: str,
        reproduction_steps: list[str],
        poc_curl: str,
        remediation: str,
        program: str,
        platform: str,
        cvss_score: float | None = None,
    ) -> dict[str, str]:
        result = {
            "hackerone_json": self.to_hackerone_json(
                title, narrative, severity, cvss, affected_endpoint,
                affected_method, reproduction_steps, poc_curl, remediation,
            ),
            "markdown": self.to_markdown(
                title, narrative, severity, cvss, affected_endpoint,
                affected_method, reproduction_steps, poc_curl, remediation,
            ),
            "bugcrowd_html": self.to_bugcrowd_html(
                title, narrative, severity, cvss, affected_endpoint,
                affected_method, reproduction_steps, poc_curl, remediation,
                program, platform,
            ),
        }
        html_jinja = self.to_html_jinja(
            title, narrative, severity, cvss, affected_endpoint,
            affected_method, reproduction_steps, poc_curl, remediation,
            program, platform, cvss_score=cvss_score,
        )
        if html_jinja is not None:
            result["html_jinja"] = html_jinja
        return result

    def to_html_jinja(
        self,
        title: str,
        narrative: str,
        severity: str,
        cvss: str,
        affected_endpoint: str,
        affected_method: str,
        reproduction_steps: list[str],
        poc_curl: str,
        remediation: str,
        program: str,
        platform: str,
        cvss_score: float | None = None,
    ) -> str | None:
        if self._jinja_env is None:
            return None
        try:
            tmpl = self._jinja_env.get_template("report.html")
            return tmpl.render(
                title=title,
                narrative=narrative,
                severity=severity,
                cvss=cvss,
                cvss_score=cvss_score,
                affected_endpoint=affected_endpoint,
                affected_method=affected_method,
                reproduction_steps=reproduction_steps,
                poc_curl=poc_curl,
                remediation=remediation,
                program=program,
                platform=platform,
            )
        except Exception:
            return None

    def to_hackerone_json(
        self,
        title: str,
        narrative: str,
        severity: str,
        cvss: str,
        affected_endpoint: str,
        affected_method: str,
        reproduction_steps: list[str],
        poc_curl: str,
        remediation: str,
    ) -> str:
        report = {
            "vulnerability_information": f"{narrative}\n\n## Reproduction\n\n"
            + "\n".join(reproduction_steps)
            + f"\n\n## PoC\n\n```bash\n{poc_curl}\n```\n\n## Remediation\n\n{remediation}",
            "severity_rating": severity.upper(),
            "cvss_vector": cvss,
            "weakness": {
                "id": None,
                "name": title.split(" in ")[0] if " in " in title else "Security Finding",
            },
            "impact": narrative,
            "reproduction_steps": "\n".join(reproduction_steps),
            "impacted_url": affected_endpoint,
            "impacted_method": affected_method,
        }
        return json.dumps(report, indent=2, ensure_ascii=False)

    def to_markdown(
        self,
        title: str,
        narrative: str,
        severity: str,
        cvss: str,
        affected_endpoint: str,
        affected_method: str,
        reproduction_steps: list[str],
        poc_curl: str,
        remediation: str,
    ) -> str:
        steps = "\n".join(f"- {s.strip('0123456789. ')}" for s in reproduction_steps)
        return (
            f"# {title}\n\n"
            f"**Severity:** {severity.upper()}  \n"
            f"**CVSS:** {cvss}  \n"
            f"**Endpoint:** `{affected_method} {affected_endpoint}`  \n\n"
            f"## Description\n{narrative}\n\n"
            f"## Reproduction\n{steps}\n\n"
            f"## Proof of Concept\n```bash\n{poc_curl}\n```\n\n"
            f"## Remediation\n{remediation}\n"
        )

    def to_bugcrowd_html(
        self,
        title: str,
        narrative: str,
        severity: str,
        cvss: str,
        affected_endpoint: str,
        affected_method: str,
        reproduction_steps: list[str],
        poc_curl: str,
        remediation: str,
        program: str,
        platform: str,
    ) -> str:
        steps = "".join(f"<li>{s.strip('0123456789. ')}</li>" for s in reproduction_steps)
        return (
            f"<h1>{title}</h1>\n"
            f"<p><strong>Program:</strong> {program} ({platform})</p>\n"
            f"<p><strong>Severity:</strong> {severity.upper()}</p>\n"
            f"<p><strong>CVSS:</strong> {cvss}</p>\n"
            f"<p><strong>Endpoint:</strong> <code>{affected_method} {affected_endpoint}</code></p>\n"
            f"<h2>Description</h2>\n<p>{narrative}</p>\n"
            f"<h2>Reproduction</h2>\n<ol>{steps}</ol>\n"
            f"<h2>Proof of Concept</h2>\n<pre><code>{poc_curl}</code></pre>\n"
            f"<h2>Remediation</h2>\n<p>{remediation}</p>\n"
        )
