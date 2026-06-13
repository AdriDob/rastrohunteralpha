"""Tests for the unified scoring engine."""

from __future__ import annotations


class TestUnifiedScoring:
    """Verify the unified scoring engine produces consistent results."""

    def test_score_endpoint_basic(self):
        from core.engine.unified_scoring import score
        result = score("/api/login", "POST", {})
        assert isinstance(result, dict)
        assert "risk_score" in result
        assert isinstance(result["risk_score"], (int, float))
        assert result["risk_score"] >= 0

    def test_score_auth_endpoint_higher_risk(self):
        from core.engine.unified_scoring import score
        basic = score("/", "GET", {})
        auth = score("/admin", "GET", {})
        assert auth["risk_score"] >= basic["risk_score"]

    def test_score_graphql_elevated(self):
        from core.engine.unified_scoring import score
        gql = score("/graphql", "POST", {})
        basic = score("/", "GET", {})
        assert gql["risk_score"] >= basic["risk_score"]

    def test_score_known_vectors(self):
        from core.engine.unified_scoring import score
        vectors = score("/api/v1/users", "GET", {})
        assert vectors.get("vector") is not None

    def test_score_target(self):
        from core.engine.unified_scoring import score_target
        result = score_target({
            "api_count": 10,
            "has_graphql": True,
            "has_admin": True,
            "has_api": True,
            "has_exports": False,
            "source": "test_target",
        })
        assert isinstance(result, dict)
        assert "roi_score" in result
        assert "priority" in result
        assert "quality" in result
        assert isinstance(result["roi_score"], (int, float))
        assert result["roi_score"] >= 0

    def test_score_target_empty(self):
        from core.engine.unified_scoring import score_target
        result = score_target({})
        assert isinstance(result, dict)
        assert result["roi_score"] >= 0

    def test_score_target_no_api(self):
        from core.engine.unified_scoring import score_target
        low = score_target({
            "api_count": 0,
            "has_graphql": False,
            "has_admin": False,
            "has_api": False,
            "has_exports": False,
            "source": "basic_target",
        })
        assert low["roi_score"] >= 0

    def test_overview_integration(self):
        from api.routers.overview import get_overview
        result = get_overview()
        assert isinstance(result, dict)
        assert "target_count" in result
        assert "endpoint_count" in result
        assert "risk_distribution" in result
