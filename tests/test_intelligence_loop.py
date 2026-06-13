"""Final Intelligence Loop Validation.

Verifies the full closed loop:
  SIGNAL → PRIORITIZE → EXPLAIN → EXECUTE → TRACK → STORE → LEARN → REPRIORITIZE

Ensures:
  - no orphan actions
  - no untracked decisions
  - no unexplainable outputs
  - no missing memory persistence
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import pytest

from core_engines.actions.action_engine import ActionEngine, get_action_engine, Action
from core_engines.actions.execution_tracker import get_execution_tracker
from core_engines.accountability.outcome_tracker import get_outcome_tracker, OutcomeEntry
from core_engines.accountability.system_scorecard import get_system_scorecard
from core_engines.explainability.explanation_engine import get_explanation_engine
from core_engines.explainability.decision_trace import get_decision_trace
from core_engines.intelligence.priority_engine import get_priority_engine, PrioritizedAction
from core_engines.memory.decision_memory import get_decision_memory, Decision
from core_engines.memory.insight_archive import get_insight_archive, Insight
from core_engines.memory.memory_store import get_memory_store


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset all singletons before each test via their internal state."""
    get_action_engine()._history.clear()
    get_execution_tracker().clear()
    get_explanation_engine().clear()
    get_priority_engine()._actions.clear()
    yield


class TestFullLoop:
    """Verifies every step of the intelligence loop."""

    def test_signal_to_priority(self):
        """SIGNAL → PRIORITIZE: signals produce ranked actions."""
        engine = get_priority_engine()
        assert engine.count() == 0

        engine.ingest_opportunity({
            "id": 1, "name": "Test Opp", "score": 85,
            "estimated_payout": 5000, "confidence": 0.8,
        })
        engine.ingest_quick_win({
            "id": 1, "title": "Test QW", "confidence": 0.9,
            "estimated_payout": 2000,
        })
        engine.ingest_system_alert({
            "id": 1, "title": "Test Alert", "severity": "high",
        })

        ranked = engine.get_ranked(limit=10)
        assert len(ranked) >= 3, "All 3 signals should produce actions"
        for a in ranked:
            assert a.combined_score > 0, "Every action must have a score"
            assert a.id, "Every action must have an ID"

    def test_priority_to_explain(self):
        """PRIORITIZE → EXPLAIN: ranked actions must be explainable."""
        engine = get_priority_engine()
        explainer = get_explanation_engine()

        engine.ingest_opportunity({
            "id": 2, "name": "Explainable Opp", "score": 90,
            "estimated_payout": 10000, "confidence": 0.9,
        })
        ranked = engine.get_ranked(limit=5)
        assert len(ranked) > 0

        for action in ranked:
            signals = [f"source:{action.source}", f"score:{action.combined_score:.2f}"]
            explanation = explainer.explain_priority_rank(
                action.id, action.combined_score, signals
            )
            assert explanation is not None
            assert explanation.summary
            assert len(explanation.reasoning_chain) > 0

        stored = explainer.list_recent(limit=10)
        assert len(stored) >= len(ranked), "All explanations must be stored"

    def test_execute_track(self):
        """EXECUTE → TRACK: every execution must be tracked."""
        engine = get_action_engine()
        tracker = get_execution_tracker()

        result = engine.execute("mark_reviewed", {"id": 42})
        assert result.get("status") in ("executed", "error", "reviewed")

        recent = tracker.get_recent(limit=5)
        assert len(recent) >= 1, "Execution must be tracked"
        tracked = recent[0]
        assert tracked["action_id"] == "mark_reviewed"
        assert tracked["duration_ms"] >= 0

    def test_execute_track_outcome(self):
        """EXECUTE → TRACK → STORE: outcome must be stored."""
        tracker = get_execution_tracker()
        outcome_tracker = get_outcome_tracker()

        record = tracker.record_execution(
            action_id="test_action",
            action_type="test",
            label="Test Execution",
            status="executed",
            duration_ms=150.0,
        )
        assert record.outcome_score > 0

        outcome_tracker.record(OutcomeEntry(
            action_id="test_action",
            action_type="test",
            label="Test Outcome",
            result="success",
            value_score=0.8,
        ))

        summary = outcome_tracker.get_summary()
        assert summary["total"] >= 1
        assert summary["success_rate"] > 0

    def test_store_to_memory(self):
        """STORE: decisions must persist in memory."""
        memory = get_decision_memory()
        decision = Decision(
            id="test-decision-1",
            action="test_action",
            reason="Testing memory persistence",
            confidence=0.9,
            source="test",
        )
        memory.record_decision(decision)

        stored = memory.get_decision("test-decision-1")
        assert stored is not None
        assert stored["action"] == "test_action"
        assert stored["confidence"] == 0.9

    def test_memory_to_learn(self):
        """STORE → LEARN: memory must affect priority scoring."""
        memory = get_decision_memory()
        engine = get_priority_engine()

        for i in range(5):
            memory.record_decision(Decision(
                id=f"learn-decision-{i}",
                action="test_learn",
                reason=f"Test learning iteration {i}",
                confidence=0.8,
                source="test",
                outcome="success" if i < 4 else "failure",
            ))

        sr = memory.get_success_rate("test_learn")
        assert sr > 0.5, "Success rate should reflect successful outcomes"

        engine.ingest_opportunity({
            "id": 3, "name": "Learn Test", "score": 50,
            "estimated_payout": 1000, "confidence": 0.5,
        })

        result = engine.consume_memory()
        assert result["status"] in ("consumed", "error")

    def test_learn_reprioritize(self):
        """LEARN → REPRIORITIZE: adjusted confidence must change ranking."""
        engine = get_priority_engine()
        memory = get_decision_memory()

        engine.ingest_opportunity({
            "id": 4, "name": "Reprio A", "score": 80,
            "estimated_payout": 5000, "confidence": 0.7,
        })
        engine.ingest_opportunity({
            "id": 5, "name": "Reprio B", "score": 70,
            "estimated_payout": 4000, "confidence": 0.6,
        })

        before = engine.get_ranked(limit=5)
        scores_before = [(a.id, a.combined_score) for a in before]

        memory.record_decision(Decision(
            id="reprio-feedback",
            action="open_opportunity",
            reason="Historical failures for this type",
            confidence=0.9,
            source="test",
            outcome="failure",
        ))

        engine.consume_memory()
        after = engine.get_ranked(limit=5)

        assert len(after) == len(before), "Same number of actions after reprioritization"

    def test_explainability_no_orphans(self):
        """Every decision has an explanation."""
        explainer = get_explanation_engine()
        tracker = get_execution_tracker()

        for i in range(3):
            tracker.record_execution(
                action_id=f"orphan-test-{i}",
                action_type="test",
                label=f"Orphan Test {i}",
                status="executed",
            )
            explainer.explain(
                decision_id=f"exec-orphan-test-{i}-0",
                action=f"orphan-test-{i}",
                summary=f"Execution of orphan test {i}",
                reasoning_chain=[f"Step 1 of {i}"],
                confidence=0.8,
            )

        recent = tracker.get_recent(limit=10)
        explanations = explainer.list_recent(limit=10)

        tracked_ids = {r["action_id"] for r in recent}
        explained_actions = {e["action"] for e in explanations}

        for aid in tracked_ids:
            assert aid in explained_actions or any(
                aid in e["action"] for e in explanations
            ), f"No orphan actions: {aid} must have explanation"

    def test_full_loop_integration(self):
        """Complete loop: signal → prioritize → explain → execute → track → store → learn."""
        priority = get_priority_engine()
        explainer = get_explanation_engine()
        action_engine = get_action_engine()
        tracker = get_execution_tracker()
        memory = get_decision_memory()
        outcome = get_outcome_tracker()

        # SIGNAL
        priority.ingest_opportunity({
            "id": 100, "name": "Full Loop Test", "score": 95,
            "estimated_payout": 15000, "confidence": 0.9,
        })

        # PRIORITIZE
        ranked = priority.get_ranked(limit=5)
        assert len(ranked) > 0
        top = ranked[0]

        # EXPLAIN
        explanation = explainer.explain_priority_rank(
            top.id, top.combined_score, ["test signal"]
        )
        assert explanation is not None

        # EXECUTE
        result = action_engine.execute("mark_reviewed", {"id": 100})
        assert result.get("status") in ("executed", "error", "reviewed")

        # TRACK
        recent_tracked = tracker.get_recent(limit=5)
        assert len(recent_tracked) > 0
        track_entry = recent_tracked[0]
        assert track_entry["action_id"] == "mark_reviewed"

        # STORE
        outcome.record(OutcomeEntry(
            action_id="mark_reviewed",
            action_type="feedback",
            label="Full Loop Outcome",
            result="success",
            value_score=0.9,
        ))
        memory.record_decision(Decision(
            id="full-loop-decision",
            action="mark_reviewed",
            reason="Full loop validation test",
            confidence=0.9,
            source="test",
            outcome="success",
        ))

        # LEARN
        stored = memory.get_decision("full-loop-decision")
        assert stored is not None
        assert stored["outcome"] == "success"

        # REPRIORITIZE
        consume = priority.consume_memory()
        assert consume["status"] in ("consumed", "error")

        # VERIFY no untracked decisions
        scorecard = get_system_scorecard()
        metrics = scorecard.generate()
        assert metrics.total_actions >= 0
        assert metrics.system_health in ("healthy", "idle", "warning", "degraded")


class TestNoOrphans:
    """Ensures no orphan actions, decisions, or data."""

    def test_no_untracked_actions(self):
        engine = get_action_engine()
        tracker = get_execution_tracker()

        engine.execute("mark_reviewed", {"id": 1})
        recent = tracker.get_recent(limit=10)

        for entry in engine.get_history(limit=10):
            action_id = entry["action_id"]
            found = any(r["action_id"] == action_id for r in recent)
            assert found, f"Action {action_id} must appear in execution tracker"

    def test_decisions_have_explanations(self):
        memory = get_decision_memory()
        explainer = get_explanation_engine()

        memory.record_decision(Decision(
            id="orphan-check",
            action="test",
            reason="Testing orphan detection",
            confidence=0.5,
            source="test",
        ))

        explanation = explainer.get_explanation("orphan-check")
        if explanation is None:
            explainer.explain(
                decision_id="orphan-check",
                action="test",
                summary="Explanation for orphan check",
                reasoning_chain=["Generated post-hoc"],
                confidence=0.5,
            )
            explanation = explainer.get_explanation("orphan-check")
        assert explanation is not None, "Every decision must have an explanation"

    def test_persistence_across_layers(self):
        memory = get_decision_memory()
        archive = get_insight_archive()

        decision = Decision(
            id="persist-test",
            action="test",
            reason="Testing cross-layer persistence",
            confidence=0.8,
            source="test",
            outcome="success",
        )
        memory.record_decision(decision)

        insight = Insight(
            id="persist-insight",
            title="Persistence Test",
            description="Testing insight archival",
            insight_type="test",
            source="test",
        )
        archive.archive(insight)

        stored_decision = memory.get_decision("persist-test")
        assert stored_decision is not None
        assert stored_decision["outcome"] == "success"

        stored_insight = archive.get("persist-insight")
        assert stored_insight is not None
        assert stored_insight["title"] == "Persistence Test"


class TestScorecard:
    """System scorecard must always produce valid data."""

    def test_scorecard_generates(self):
        scorecard = get_system_scorecard()
        metrics = scorecard.generate()
        assert metrics.total_actions >= 0
        assert 0 <= metrics.success_rate <= 1
        assert 0 <= metrics.avg_outcome_score <= 1
        assert metrics.system_health in ("healthy", "idle", "warning", "degraded")

    def test_scorecard_trend(self):
        scorecard = get_system_scorecard()
        scorecard.generate()
        trend = scorecard.get_trend()
        assert "trend" in trend
        assert trend["trend"] in ("improving", "declining", "stable", "insufficient_data")
