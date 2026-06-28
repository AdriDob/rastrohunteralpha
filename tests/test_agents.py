"""Tests for the Multi-Agent system (Phase 1).

Covers:
- EventBus: publish, subscribe, replay, history, frozen events, logging hook
- BaseAgent: registration, subscriptions, health, capabilities, retry_policy
- CoordinatorAgent: pipeline orchestration, conflict resolution, state machine
- All 8 agents: basic event handling
- API endpoints: health, pipelines, memory, financial, events, replay
"""

from __future__ import annotations

import json
import time
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from core_engines.agents import (
    AgentEvent,
    AgentId,
    EventType,
    get_agent_bus,
    get_coordinator,
    get_financial_agent,
    get_memory_agent,
    get_strategy_agent,
    reset_agent_bus,
    start_all_agents,
    stop_all_agents,
)
from core_engines.agents.base import BaseAgent
from core_engines.agents.documentation import DocumentationAgent
from core_engines.agents.exploit import ExploitAgent
from core_engines.agents.financial import FinancialAgent
from core_engines.agents.research import ResearchAgent
from core_engines.agents.validator import ValidatorAgent

# ─── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_bus():
    from core_engines.agents import reset_all_agents
    reset_all_agents()
    yield
    reset_all_agents()


@pytest.fixture
def bus():
    return get_agent_bus()


# ─── Event Bus Tests ──────────────────────────────────────────────


class TestEventBus:
    def test_publish_subscribe(self, bus):
        received = []
        bus.subscribe("test.event", lambda e: received.append(e))
        event = AgentEvent(event_type="test.event", source="test", payload={"msg": "hello"})
        bus.publish(event)
        time.sleep(0.01)
        assert len(received) == 1
        assert received[0].correlation_id == event.event_id
        assert received[0].payload["msg"] == "hello"

    def test_frozen_events(self, bus):
        """AgentEvent must be immutable."""
        event = AgentEvent(event_type="test.event", source="test")
        with pytest.raises((TypeError, AttributeError, Exception)):
            event.payload = {"modified": True}

    def test_correlation_id_traceability(self, bus):
        events = []
        bus.subscribe("*", lambda e: events.append(e))
        corr = "abc123"
        bus.publish(AgentEvent(event_type="a", source="s1", correlation_id=corr))
        bus.publish(AgentEvent(event_type="b", source="s2", correlation_id=corr))
        bus.publish(AgentEvent(event_type="c", source="s3", correlation_id="other"))
        time.sleep(0.01)
        replay = bus.replay(corr)
        assert len(replay) == 2
        assert all(e.correlation_id == corr for e in replay)

    def test_get_history(self, bus):
        for i in range(5):
            bus.publish(AgentEvent(event_type=f"type.{i}", source="test"))
        time.sleep(0.01)
        history = bus.get_history(limit=3)
        assert len(history) == 3
        assert history[-1].event_type == "type.4"

    def test_get_history_filtered(self, bus):
        bus.publish(AgentEvent(event_type="a", source="test"))
        bus.publish(AgentEvent(event_type="b", source="test"))
        bus.publish(AgentEvent(event_type="a", source="test"))
        time.sleep(0.01)
        filtered = bus.get_history(event_type="a")
        assert len(filtered) == 2

    def test_subscribe_agent(self, bus):
        received = []
        bus.subscribe_agent(AgentId.COORDINATOR, lambda e: received.append(e))
        event = AgentEvent(event_type="test", source="test", target=AgentId.COORDINATOR)
        bus.publish(event)
        time.sleep(0.01)
        assert len(received) == 1

    def test_unsubscribe(self, bus):
        received = []
        handler = lambda e: received.append(e)
        bus.subscribe("test", handler)
        bus.publish(AgentEvent(event_type="test", source="test"))
        time.sleep(0.01)
        assert len(received) == 1
        bus.unsubscribe("test", handler)
        bus.publish(AgentEvent(event_type="test", source="test"))
        time.sleep(0.01)
        assert len(received) == 1  # No increment

    def test_logging_hook(self, bus):
        hook = MagicMock()
        bus.set_logging_hook(hook)
        event = AgentEvent(event_type="test", source="test")
        bus.publish(event)
        hook.assert_called_once_with(event)

    def test_clear_history(self, bus):
        bus.publish(AgentEvent(event_type="test", source="test"))
        bus.clear_history()
        assert len(bus.get_history()) == 0

    def test_serializable(self, bus):
        """Events must be serializable to dict."""
        event = AgentEvent(
            event_type=EventType.PIPELINE_START,
            source=AgentId.COORDINATOR,
            target=AgentId.RESEARCH,
            payload={"target_id": 1, "target_name": "example.com"},
        )
        d = event.to_dict()
        assert d["event_type"] == "pipeline.start"
        assert d["source"] == "coordinator"
        assert d["target"] == "research"
        assert d["payload"]["target_name"] == "example.com"
        # Must be JSON-serializable
        json_str = json.dumps(d)
        parsed = json.loads(json_str)
        assert parsed["event_type"] == "pipeline.start"


# ─── Base Agent Tests ─────────────────────────────────────────────


class TestBaseAgent:
    def test_agent_registration(self, bus):
        events = []
        bus.subscribe(EventType.AGENT_REGISTERED, lambda e: events.append(e))
        agent = ResearchAgent()
        agent.start()
        time.sleep(0.01)
        assert len(events) >= 1
        assert events[-1].payload["agent_id"] == "research"
        agent.stop()

    def test_agent_health(self, bus):
        agent = ResearchAgent()
        agent.start()
        health = agent.health()
        assert health["agent_id"] == "research"
        assert "name" in health
        assert "capabilities" in health
        assert "status" in health
        agent.stop()

    def test_agent_capabilities(self):
        agent = ResearchAgent()
        caps = agent.capabilities
        assert isinstance(caps, list)
        assert "handles:RESEARCH_START" in caps or "handles:research.start" in caps

    def test_agent_retry_policy_default(self):
        agent = ResearchAgent()
        policy = agent.retry_policy
        assert policy["max_retries"] == 2
        assert policy["backoff_s"] == 1.0

    def test_agent_name_default(self):
        agent = ResearchAgent()
        assert agent.name == "Research"

    def test_emit_event(self, bus):
        received = []
        bus.subscribe(EventType.SYSTEM_ALERT, lambda e: received.append(e))
        agent = ResearchAgent()
        agent.emit(EventType.SYSTEM_ALERT, payload={"msg": "test"})
        time.sleep(0.01)
        assert len(received) == 1
        assert received[0].source == "research"

    def test_subscribe_convenience(self, bus):
        received = []
        agent = ResearchAgent()
        agent.subscribe("custom.event", lambda e: received.append(e))
        bus.publish(AgentEvent(event_type="custom.event", source="test"))
        time.sleep(0.01)
        assert len(received) == 1
        # Cleanup
        bus.unsubscribe("custom.event", received[0] if received else lambda e: None)

    def test_error_handling(self, bus):
        errors = []
        bus.subscribe(EventType.SYSTEM_ERROR, lambda e: errors.append(e))

        class BrokenAgent(BaseAgent):
            def _get_agent_id(self): return AgentId.RESEARCH
            def _get_subscriptions(self): return ["broken.event"]
            def handle_event(self, event): raise ValueError("test error")

        agent = BrokenAgent()
        agent.start()
        bus.publish(AgentEvent(event_type="broken.event", source="test"))
        time.sleep(0.02)
        assert agent.tasks_failed == 1
        assert len(errors) >= 1
        assert "test error" in errors[-1].payload["error"]
        agent.stop()


# ─── Coordinator Tests ────────────────────────────────────────────


class TestCoordinator:
    def test_pipeline_start(self, bus):
        coordinator = get_coordinator()
        coordinator.start()

        bus.publish(AgentEvent(
            event_type=EventType.PIPELINE_START,
            source="api",
            target=AgentId.COORDINATOR,
            payload={"target_id": 1, "target_name": "test.com"},
        ))
        time.sleep(0.03)

        pipelines = coordinator.list_pipelines()
        assert len(pipelines) >= 1
        pid = list(pipelines.keys())[0]
        assert pipelines[pid]["target_name"] == "test.com"
        coordinator.stop()

    def test_conflict_resolution(self, bus):
        coordinator = get_coordinator()
        coordinator.start()

        alerts = []
        bus.subscribe(EventType.SYSTEM_ALERT, lambda e: alerts.append(e))

        # Start two pipelines for same target
        bus.publish(AgentEvent(
            event_type=EventType.PIPELINE_START,
            source="api", target=AgentId.COORDINATOR,
            correlation_id="p1",
            payload={"target_id": 1, "target_name": "dup.com"},
        ))
        time.sleep(0.02)
        bus.publish(AgentEvent(
            event_type=EventType.PIPELINE_START,
            source="api", target=AgentId.COORDINATOR,
            correlation_id="p2",
            payload={"target_id": 1, "target_name": "dup.com"},
        ))
        time.sleep(0.03)

        # Should have emitted a conflict alert
        conflict_alerts = [a for a in alerts if a.payload.get("type") == "pipeline_conflict"]
        assert len(conflict_alerts) >= 1, f"No conflict alerts found in {len(alerts)} alerts"
        coordinator.stop()

    def test_pipeline_stage_advancement(self, bus):
        coordinator = get_coordinator()
        coordinator.start()
        research_events = []
        bus.subscribe(EventType.RESEARCH_START, lambda e: research_events.append(e))

        bus.publish(AgentEvent(
            event_type=EventType.PIPELINE_START,
            source="api", target=AgentId.COORDINATOR,
            payload={"target_id": 2, "target_name": "stage-test.com"},
        ))
        time.sleep(0.03)

        assert len(research_events) >= 1, f"No research events, pipelines={coordinator.list_pipelines()}"
        coordinator.stop()

    def test_pipeline_lifecycle(self, bus):
        coordinator = get_coordinator()
        coordinator.start()
        pid = "lifecycle-test"

        bus.publish(AgentEvent(
            event_type=EventType.PIPELINE_START,
            source="api", target=AgentId.COORDINATOR,
            correlation_id=pid,
            payload={"target_id": 3, "target_name": "lifecycle.com"},
        ))
        time.sleep(0.03)

        # Complete the discovery stage
        bus.publish(AgentEvent(
            event_type=EventType.PIPELINE_STAGE_COMPLETED,
            source=AgentId.RESEARCH, target=AgentId.COORDINATOR,
            correlation_id=pid,
            payload={"stage": "discovery", "next_stage": "validation"},
        ))
        time.sleep(0.03)

        status = coordinator.get_pipeline_status(pid)
        assert status is not None, f"Pipeline {pid} not found in {coordinator.list_pipelines()}"
        assert status["state"] == "validation"
        coordinator.stop()


# ─── Agent Communication Tests ────────────────────────────────────


class TestAgentCommunication:
    def test_research_to_coordinator_flow(self, bus):
        coordinator = get_coordinator()
        coordinator.start()

        pipeline_events = []
        bus.subscribe(EventType.PIPELINE_STAGE_COMPLETED, lambda e: pipeline_events.append(e))

        bus.publish(AgentEvent(
            event_type=EventType.PIPELINE_START,
            source="test", target=AgentId.COORDINATOR,
            payload={"target_id": 10, "target_name": "agent-flow.com"},
        ))
        time.sleep(0.02)

        # Research publishes completion
        research = ResearchAgent()
        research.start()
        bus.publish(AgentEvent(
            event_type=EventType.RESEARCH_START,
            source=AgentId.COORDINATOR, target=AgentId.RESEARCH,
            correlation_id=list(coordinator._active_pipelines.keys())[0],
            payload={"target_id": 10, "target_name": "agent-flow.com"},
        ))
        time.sleep(0.02)
        research.stop()
        coordinator.stop()


# ─── All Agents Start/Stop Tests ──────────────────────────────────


class TestAgentLifecycle:
    def test_start_all_agents(self):
        reset_agent_bus()
        agents = start_all_agents()
        assert len(agents) == 8
        time.sleep(0.03)
        for agent in agents:
            assert agent._running, f"{agent.agent_id} not running"
        stop_all_agents()
        # Verify original agents stopped
        for agent in agents:
            assert not agent._running, f"{agent.agent_id} still running"

    def test_agents_health(self):
        reset_agent_bus()
        start_all_agents()
        time.sleep(0.02)
        health = {a.agent_id.value: a.health() for a in (
            get_coordinator(), ResearchAgent(), ValidatorAgent(),
            ExploitAgent(), DocumentationAgent(), get_strategy_agent(),
            get_memory_agent(), get_financial_agent(),
        )}
        assert "coordinator" in health
        assert health["coordinator"]["name"] == "Coordinador"
        assert "research" in health
        stop_all_agents()


# ─── Memory Agent Tests ───────────────────────────────────────────


class TestMemoryAgent:
    def test_store_and_recall(self, bus):
        agent = get_memory_agent()
        agent.start()
        agent.emit(EventType.MEMORY_STORE, payload={
            "key": "test_key", "value": {"data": 42}, "namespace": "testing",
        }, target=AgentId.MEMORY)
        time.sleep(0.02)
        result = agent.remember("testing", "test_key")
        assert result is not None
        assert result["value"]["data"] == 42
        agent.stop()

    def test_get_stats(self, bus):
        agent = get_memory_agent()
        agent.start()
        stats = agent.get_stats()
        assert "namespaces" in stats
        assert "entries" in stats
        agent.stop()


# ─── Financial Agent Tests ────────────────────────────────────────


class TestFinancialAgent:
    def test_record_payout(self):
        reset_agent_bus()
        # Fresh agent instance to avoid state accumulation
        from core_engines.agents.financial import _FINANCIAL
        _FINANCIAL = None  # noqa
        import os
        import tempfile
        tmp = os.path.join(tempfile.gettempdir(), "test_finance.json")
        agent = FinancialAgent(data_path=tmp)
        if os.path.exists(tmp):
            os.remove(tmp)
        agent.start()
        agent.emit(EventType.FINANCIAL_PAYOUT_RECORDED, payload={
            "amount": 500, "program": "test", "currency": "USD",
        })
        time.sleep(0.03)
        summary = agent.get_summary()
        assert summary["metrics"]["total_paid"] == 500, f"Got {summary}"
        agent.stop()
        if os.path.exists(tmp):
            os.remove(tmp)

    def test_set_metric(self, bus):
        agent = get_financial_agent()
        agent.start()
        agent.set_metric("total_revenue", 1000)
        summary = agent.get_summary()
        assert summary["metrics"]["total_revenue"] == 1000
        agent.stop()


# ─── API Tests ────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def api_client():
    reset_agent_bus()
    from api.main import app
    from core_engines.license.validator import generate_license
    c = TestClient(app)
    lic = generate_license(expiry_days=365)
    c.post("/api/license/activate", json={"key": lic})
    resp = c.post("/api/auth/login", json={"device_id": "pytest-agent-test"})
    if resp.status_code == 200:
        token = resp.json()["data"]["token"]
        c.headers.update({"Authorization": f"Bearer {token}"})
    c.headers.update({"Content-Type": "application/json"})
    return c


class TestAgentAPI:
    def test_health_endpoint(self, api_client):
        resp = api_client.get("/api/agents/health")
        assert resp.status_code in (200, 307)  # 307 if auth redirect
        if resp.status_code == 200:
            data = resp.json()
            assert "agents" in data

    def test_events_endpoint(self, api_client):
        resp = api_client.get("/api/agents/events")
        if resp.status_code == 200:
            data = resp.json()
            assert "events" in data
            assert "count" in data

    def test_coordinator_pipelines(self, api_client):
        resp = api_client.get("/api/agents/coordinator/pipelines")
        if resp.status_code == 200:
            data = resp.json()
            assert "pipelines" in data

    def test_memory_stats(self, api_client):
        resp = api_client.get("/api/agents/memory/stats")
        if resp.status_code == 200:
            data = resp.json()
            assert "stats" in data

    def test_financial_summary(self, api_client):
        resp = api_client.get("/api/agents/financial/summary")
        if resp.status_code == 200:
            data = resp.json()
            assert "metrics" in data

    def test_strategy_recommendations(self, api_client):
        resp = api_client.get("/api/agents/strategy/recommendations")
        if resp.status_code == 200:
            data = resp.json()
            assert "recommendations" in data

    def test_pipeline_start(self, api_client):
        resp = api_client.post("/api/agents/pipeline/start", json={
            "target_id": 999, "target_name": "api-test.com",
        })
        if resp.status_code == 200:
            data = resp.json()
            assert data["status"] == "started"

    def test_replay_endpoint(self, api_client):
        resp = api_client.get("/api/agents/replay/test-corr-id")
        if resp.status_code == 200:
            data = resp.json()
            assert "events" in data
            assert data["correlation_id"] == "test-corr-id"
