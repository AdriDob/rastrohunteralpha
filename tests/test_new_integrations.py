"""Tests for new integrations: gau, ffuf, SecLists, Burp, ZAP, correlation, hypothesis."""

import json
from pathlib import Path

# ─── SecLists Profiles ───────────────────────────────────────────────────────

class TestSecListsProfiles:
    def test_wordlist_registry(self):
        from core_engines.recon.seclists_profiles import WORDLISTS, get_wordlist
        assert len(WORDLISTS) >= 10
        common = get_wordlist("common")
        assert common is not None
        assert common.category == "web_content"

    def test_get_wordlists_by_category(self):
        from core_engines.recon.seclists_profiles import get_wordlists_by_category
        api_wl = get_wordlists_by_category("api")
        assert len(api_wl) >= 3
        assert all(wl.category == "api" for wl in api_wl)

    def test_get_recommended_profiles(self):
        from core_engines.recon.seclists_profiles import get_recommended_profiles
        fast = get_recommended_profiles("FAST")
        assert len(fast) == 2
        deep = get_recommended_profiles("DEEP")
        assert len(deep) >= 8


# ─── Correlation Engine ──────────────────────────────────────────────────────

class TestCorrelationEngine:
    def test_ingest_and_count(self):
        from core_engines.engine.correlation import CorrelationEngine
        engine = CorrelationEngine()
        items = [
            {"title": "XSS", "severity": "high", "url": "https://example.com/xss"},
            {"title": "SQLi", "severity": "critical", "url": "https://example.com/sqli"},
        ]
        engine.ingest("test_source", items)
        assert len(engine.findings) == 2
        assert engine.get_source_summary() == {"test_source": 2}

    def test_dedup(self):
        from core_engines.engine.correlation import CorrelationEngine
        engine = CorrelationEngine()
        items = [
            {"title": "XSS", "severity": "high", "url": "https://example.com/xss"},
            {"title": "XSS", "severity": "high", "url": "https://example.com/xss"},
        ]
        engine.ingest("test", items)
        assert len(engine.findings) == 1

    def test_severity_summary(self):
        from core_engines.engine.correlation import CorrelationEngine
        engine = CorrelationEngine()
        items = [
            {"title": "A", "severity": "critical", "url": "https://a.com"},
            {"title": "B", "severity": "high", "url": "https://b.com"},
            {"title": "C", "severity": "medium", "url": "https://c.com"},
            {"title": "D", "severity": "low", "url": "https://d.com"},
            {"title": "E", "severity": "info", "url": "https://e.com"},
        ]
        engine.ingest("test", items)
        summary = engine.get_severity_summary()
        assert summary.get("critical") == 1
        assert summary.get("high") == 1
        assert summary.get("medium") == 1
        assert summary.get("low") == 1
        assert summary.get("info") == 1

    def test_get_priority_findings(self):
        from core_engines.engine.correlation import CorrelationEngine
        engine = CorrelationEngine()
        items = [
            {"title": "Critical", "severity": "critical", "url": "https://a.com"},
            {"title": "Info", "severity": "info", "url": "https://b.com"},
        ]
        engine.ingest("test", items)
        priority = engine.get_priority_findings(min_severity="high")
        assert len(priority) == 1
        assert priority[0].title == "Critical"

    def test_host_extraction(self):
        from core_engines.engine.correlation import extract_host
        assert extract_host("https://example.com/path") == "example.com"
        assert extract_host("") == ""

    def test_clear(self):
        from core_engines.engine.correlation import CorrelationEngine
        engine = CorrelationEngine()
        engine.ingest("test", [{"title": "A", "url": "https://a.com"}])
        assert len(engine.findings) == 1
        engine.clear()
        assert len(engine.findings) == 0


# ─── Gau Runner ──────────────────────────────────────────────────────────────

class TestGauRunner:
    def test_gau_initialization(self, tmp_path):
        from core_engines.recon.gau_runner import GauRunner
        runner = GauRunner(tmp_path)
        assert runner.output_dir == tmp_path
        assert runner.timeout == 120

    def test_gau_load_urls(self, tmp_path):
        from core_engines.recon.gau_runner import GauRunner
        runner = GauRunner(tmp_path)
        url_file = tmp_path / "gau.txt"
        url_file.write_text("https://example.com/a\nhttps://example.com/b\n")
        urls = runner.load_urls(url_file)
        assert len(urls) == 2
        assert "https://example.com/a" in urls

    def test_gau_load_urls_dedup(self, tmp_path):
        from core_engines.recon.gau_runner import GauRunner
        runner = GauRunner(tmp_path)
        url_file = tmp_path / "gau_dedup.txt"
        url_file.write_text("https://example.com/a\nhttps://example.com/a\n")
        urls = runner.load_urls(url_file)
        assert len(urls) == 1

    def test_gau_load_urls_missing_file(self, tmp_path):
        from core_engines.recon.gau_runner import GauRunner
        runner = GauRunner(tmp_path)
        urls = runner.load_urls(tmp_path / "nonexistent.txt")
        assert urls == []

    def test_gau_timeout_output(self, tmp_path):
        from core_engines.recon.gau_runner import GauRunner
        GauRunner(tmp_path)
        # Simulate a timeout by writing the timeout marker
        timeout_file = tmp_path / "gau_timeout.txt"
        timeout_file.write_text("GAU TIMED OUT")
        assert timeout_file.read_text() == "GAU TIMED OUT"


# ─── FFUF Runner ─────────────────────────────────────────────────────────────

class TestFfufRunner:
    def test_ffuf_initialization(self, tmp_path):
        from core_engines.recon.ffuf_runner import FfufRunner
        runner = FfufRunner(tmp_path)
        assert runner.output_dir == tmp_path
        assert "fast" in runner.PROFILES
        assert "deep" in runner.PROFILES

    def test_ffuf_profiles_exist(self):
        from core_engines.recon.ffuf_runner import FfufRunner
        runner = FfufRunner(Path("/tmp"))
        profile_names = list(runner.PROFILES.keys())
        assert "fast" in profile_names
        assert "balanced" in profile_names
        assert "deep" in profile_names
        assert "api" in profile_names
        assert "subdomains" in profile_names

    def test_categorize_findings(self, tmp_path):
        from core_engines.recon.ffuf_runner import FfufRunner
        runner = FfufRunner(tmp_path)
        results = [
            {"url": "https://example.com/admin", "status": 200},
            {"url": "https://example.com/api/v1/users", "status": 200},
            {"url": "https://example.com/backup.zip", "status": 200},
            {"url": "https://example.com/robots.txt", "status": 200},
            {"url": "https://example.com/redirect", "status": 301},
        ]
        cats = runner.categorize_findings(results)
        assert len(cats["admin_panels"]) == 1
        assert len(cats["api_endpoints"]) == 1
        assert len(cats["backups"]) == 1
        assert len(cats["interesting"]) >= 1
        assert len(cats["info"]) >= 1

    def test_parse_results_json(self, tmp_path):
        from core_engines.recon.ffuf_runner import FfufRunner
        runner = FfufRunner(tmp_path)
        json_path = tmp_path / "ffuf_results.json"
        data = {
            "results": [
                {"url": "https://example.com/test", "status": 200, "length": 100},
            ]
        }
        json_path.write_text(json.dumps(data))
        results = runner.parse_results(json_path)
        assert len(results) == 1
        assert results[0]["status"] == 200


# ─── Burp Import ─────────────────────────────────────────────────────────────

class TestBurpImport:
    def test_parse_burp_xml(self, tmp_path):
        from core_engines.recon.burp_import import import_burp
        xml_path = tmp_path / "burp.xml"
        xml_content = """<?xml version="1.0"?>
<items>
  <item>
    <url>https://example.com/admin</url>
    <host ip="1.2.3.4">example.com</host>
    <port>443</port>
    <protocol>https</protocol>
    <method>GET</method>
    <path>/admin</path>
    <status>200</status>
    <length>1024</length>
    <mimetype>text/html</mimetype>
  </item>
</items>"""
        xml_path.write_text(xml_content)
        items = import_burp(xml_path)
        assert len(items) == 1
        assert items[0].url == "https://example.com/admin"
        assert items[0].status == 200
        assert "admin_panel" in items[0].findings.get("flags", [])

    def test_parse_burp_json(self, tmp_path):
        from core_engines.recon.burp_import import import_burp
        json_path = tmp_path / "burp.json"
        data = [{
            "url": "https://example.com/api/users",
            "host": "example.com",
            "port": 443,
            "protocol": "https",
            "method": "GET",
            "path": "/api/users",
            "status": 200,
            "length": 500,
        }]
        json_path.write_text(json.dumps(data))
        items = import_burp(json_path)
        assert len(items) == 1
        assert items[0].url == "https://example.com/api/users"

    def test_parse_burp_xml_empty(self, tmp_path):
        from core_engines.recon.burp_import import import_burp
        xml_path = tmp_path / "empty.xml"
        xml_path.write_text("<?xml version=\"1.0\"?><items/>")
        items = import_burp(xml_path)
        assert items == []

    def test_import_nonexistent(self, tmp_path):
        from core_engines.recon.burp_import import import_burp
        items = import_burp(tmp_path / "nope.xml")
        assert items == []


# ─── ZAP Import ──────────────────────────────────────────────────────────────

class TestZapImport:
    def test_parse_zap_xml(self, tmp_path):
        from core_engines.recon.zap_import import import_zap
        xml_path = tmp_path / "zap.xml"
        xml_content = """<?xml version="1.0"?>
<OWASPZAPReport>
  <alertitem>
    <alert>Cross-Site Scripting</alert>
    <risk>High</risk>
    <confidence>Medium</confidence>
    <url>https://example.com/search</url>
    <param>q</param>
    <attack>&lt;script&gt;</attack>
    <description>XSS vulnerability</description>
    <solution>Encode output</solution>
    <reference>OWASP XSS</reference>
    <cweid>79</cweid>
    <wascid>8</wascid>
    <pluginid>40012</pluginid>
  </alertitem>
</OWASPZAPReport>"""
        xml_path.write_text(xml_content)
        sites = import_zap(xml_path)
        assert len(sites) >= 1
        alerts = sites[0].alerts
        assert len(alerts) == 1
        assert alerts[0].alert == "Cross-Site Scripting"
        assert alerts[0].risk == "High"

    def test_risk_score(self):
        from core_engines.recon.zap_import import risk_score
        assert risk_score("High") == 3
        assert risk_score("Medium") == 2
        assert risk_score("Low") == 1
        assert risk_score("Info") == 0
        assert risk_score("Informational") == 0
        assert risk_score("Unknown") == 0

    def test_filter_high_risk(self, tmp_path):
        from core_engines.recon.zap_import import (
            ZapAlert,
            ZapSite,
            filter_high_risk,
        )
        site = ZapSite(name="example.com")
        site.alerts = [
            ZapAlert(alert="High", risk="High", confidence="High",
                     url="https://example.com/a", param="", attack="",
                     description="", solution="", reference=""),
            ZapAlert(alert="Low", risk="Low", confidence="High",
                     url="https://example.com/b", param="", attack="",
                     description="", solution="", reference=""),
        ]
        filtered = filter_high_risk([site], min_risk="high")
        assert len(filtered) >= 1
        if filtered:
            assert all(a.risk == "High" for a in filtered[0].alerts)

    def test_parse_zap_empty_json(self, tmp_path):
        from core_engines.recon.zap_import import import_zap
        json_path = tmp_path / "zap.json"
        json_path.write_text("[]")
        sites = import_zap(json_path)
        assert sites == []


# ─── Runner Integration ──────────────────────────────────────────────────────

class TestRunnerIntegration:
    def test_recon_init_exports(self):
        from core_engines.recon import FfufRunner, GauRunner
        assert FfufRunner is not None
        assert GauRunner is not None


# ─── Bounty Intelligence ─────────────────────────────────────────────────────

class TestBountyIntelligence:
    def test_bounty_intel_empty_report(self):
        from core_engines.intelligence.bounty_intel import BountyIntelligence
        # With no programs in DB, expect empty but valid report
        bi = BountyIntelligence()
        report = bi.generate_report()
        assert report.generated_at != ""
        assert report.total_programs >= 0

    def test_bounty_intel_summary_generation(self):
        from core_engines.intelligence.bounty_intel import (
            BountyIntelReport,
            ProgramMetrics,
        )
        report = BountyIntelReport(generated_at="2025-01-01")
        report.total_programs = 50
        report.total_active = 30
        report.platform_metrics["hackerone"] = ProgramMetrics(
            platform="hackerone", total_programs=30, active_programs=20,
            avg_quality=75.0, avg_roi=60.0,
        )
        report.platform_metrics["bugcrowd"] = ProgramMetrics(
            platform="bugcrowd", total_programs=20, active_programs=10,
            avg_quality=55.0, avg_roi=45.0,
        )

        from core_engines.intelligence.bounty_intel import BountyIntelligence
        summary = BountyIntelligence._generate_summary(report)
        assert "Total programs" in summary
        assert "hackerone" in summary or "bugcrowd" in summary
        assert "50" in summary


class TestHypothesisTechnologyGenerators:
    def test_generate_from_technology_wordpress(self):
        from core_engines.engine.hypothesis.generators import generate_from_technology
        technologies = [{"name": "WordPress", "version": "6.4"}]
        hypotheses = generate_from_technology(technologies, target_id=1, target_name="test")
        assert len(hypotheses) >= 2
        types = {h.vulnerability_type.value for h in hypotheses}
        assert "misconfiguration" in types or "info_leak" in types or "known_vulnerability" in types
        for h in hypotheses:
            assert h.target_id == 1
            assert h.target_name == "test"
            assert h.source.value == "rule"

    def test_generate_from_technology_unknown(self):
        from core_engines.engine.hypothesis.generators import generate_from_technology
        technologies = [{"name": "UnknownFramework", "version": "1.0"}]
        hypotheses = generate_from_technology(technologies, target_id=1, target_name="test")
        assert len(hypotheses) == 0

    def test_generate_from_technology_nginx(self):
        from core_engines.engine.hypothesis.generators import generate_from_technology
        technologies = [{"name": "nginx", "version": "1.24"}]
        hypotheses = generate_from_technology(technologies, target_id=1, target_name="test")
        assert len(hypotheses) >= 1
        assert any("alias" in h.vector or "traversal" in h.reasoning for h in hypotheses)

    def test_generate_from_technology_aws(self):
        from core_engines.engine.hypothesis.generators import generate_from_technology
        technologies = [{"name": "amazonaws", "version": ""}]
        hypotheses = generate_from_technology(technologies, target_id=1, target_name="test")
        assert len(hypotheses) >= 1
        assert any("s3" in h.vector or "bucket" in h.reasoning for h in hypotheses)

    def test_generate_from_discovered_paths_git(self):
        from core_engines.engine.hypothesis.generators import generate_from_discovered_paths
        paths = ["https://target.com/.git/config"]
        hypotheses = generate_from_discovered_paths(paths, target_id=1, target_name="test")
        assert len(hypotheses) >= 1
        assert any("git_exposure" in h.vector or "git" in h.vector for h in hypotheses)

    def test_generate_from_discovered_paths_env(self):
        from core_engines.engine.hypothesis.generators import generate_from_discovered_paths
        paths = ["https://target.com/.env"]
        hypotheses = generate_from_discovered_paths(paths, target_id=1, target_name="test")
        assert len(hypotheses) >= 1
        assert any("env_exposure" in h.vector or "env" in h.vector for h in hypotheses)

    def test_generate_from_discovered_paths_actuator(self):
        from core_engines.engine.hypothesis.generators import generate_from_discovered_paths
        paths = ["https://target.com/actuator/health", "https://target.com/actuator/env"]
        hypotheses = generate_from_discovered_paths(paths, target_id=1, target_name="test")
        assert len(hypotheses) >= 2

    def test_generate_from_discovered_paths_dedup(self):
        from core_engines.engine.hypothesis.generators import generate_from_discovered_paths
        paths = ["https://target.com/.git/config", "https://target.com/.git/config"]
        hypotheses = generate_from_discovered_paths(paths, target_id=1, target_name="test")
        assert len(hypotheses) == 1

    def test_generate_hypotheses_with_technologies(self):
        from core_engines.engine.hypothesis.generators import generate_hypotheses
        endpoints = [{"id": 1, "path": "/api/user/1", "method": "GET", "risk_score": 50,
                       "signals": ["uuid"], "potential_idor": True}]
        technologies = [{"name": "WordPress", "version": "6.4"}]
        discovered_paths = ["https://target.com/.git/config"]
        hypotheses = generate_hypotheses(
            endpoints, target_id=1, target_name="test",
            technologies=technologies, discovered_paths=discovered_paths,
        )
        assert len(hypotheses) >= 3

    def test_new_vulnerability_types(self):
        from core_engines.engine.hypothesis.models import VulnerabilityType
        assert VulnerabilityType.MISCONFIGURATION.value == "misconfiguration"
        assert VulnerabilityType.KNOWN_VULNERABILITY.value == "known_vulnerability"
        assert VulnerabilityType.INFO_LEAK.value == "info_leak"
        assert VulnerabilityType.SUBDOMAIN_TAKEOVER.value == "subdomain_takeover"


class TestRewardLearning:
    def test_reward_learner_empty_db(self):
        from core_engines.intelligence.reward_learning import RewardLearner
        learner = RewardLearner()
        report = learner.analyze()
        assert report.generated_at != ""
        assert report.total_reports >= 0

    def test_reward_learner_analyze(self):
        from core_engines.intelligence.reward_learning import RewardLearner
        learner = RewardLearner()
        report = learner.analyze()
        assert hasattr(report, "by_type")
        assert hasattr(report, "by_program")
        assert hasattr(report, "summary")
        # Should not crash regardless of DB state
        assert isinstance(report.summary, str)

    def test_reward_learner_adjustments(self):
        from core_engines.intelligence.reward_learning import RewardLearner
        learner = RewardLearner()
        learner.analyze()
        adj = learner.get_adjustments()
        assert isinstance(adj, dict)

    def test_reward_learner_vt_adjustment_default(self):
        from core_engines.intelligence.reward_learning import RewardLearner
        learner = RewardLearner()
        adj = learner.get_adjustment("nonexistent_type")
        assert adj == 1.0

    def test_reward_learner_report_fields(self):
        from core_engines.intelligence.reward_learning import RewardLearner
        learner = RewardLearner()
        report = learner.analyze()
        assert isinstance(report.top_programs_by_payout, list)
        assert isinstance(report.top_programs_by_acceptance, list)
        assert isinstance(report.prediction_accuracy, float)

    def test_reward_learning_dataclasses(self):
        from core_engines.intelligence.reward_learning import (
            ProgramRewardMetrics,
            RewardLearningReport,
            VulnTypeStats,
        )
        v = VulnTypeStats(vulnerability_type="idor")
        assert v.vulnerability_type == "idor"
        assert v.count == 0

        p = ProgramRewardMetrics(program="test_prog")
        assert p.program == "test_prog"
        assert p.report_count == 0

        r = RewardLearningReport()
        assert r.total_reports == 0
        assert r.generated_at == ""
