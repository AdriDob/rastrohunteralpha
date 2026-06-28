"""Multi-Agent system for autonomous bug bounty operations."""

from __future__ import annotations

import logging

from core_engines.agents.base import BaseAgent
from core_engines.agents.bus import IEventBus, LocalEventBus, get_agent_bus, reset_agent_bus
from core_engines.agents.coordinator import CoordinatorAgent, get_coordinator
from core_engines.agents.documentation import DocumentationAgent
from core_engines.agents.exploit import ExploitAgent
from core_engines.agents.financial import FinancialAgent, get_financial_agent
from core_engines.agents.memory import MemoryAgent, get_memory_agent
from core_engines.agents.research import ResearchAgent
from core_engines.agents.strategy import StrategyAgent, get_strategy_agent
from core_engines.agents.types import (
    AgentEvent,
    AgentId,
    AgentStatus,
    EventType,
    PipelineState,
)
from core_engines.agents.validator import ValidatorAgent

logger = logging.getLogger("rastro.agents")

__all__ = [
    "IEventBus", "LocalEventBus", "get_agent_bus", "reset_agent_bus",
    "AgentEvent", "AgentId", "AgentStatus", "EventType", "PipelineState",
    "BaseAgent", "CoordinatorAgent", "get_coordinator",
    "ResearchAgent", "ValidatorAgent", "ExploitAgent",
    "DocumentationAgent", "StrategyAgent", "get_strategy_agent",
    "MemoryAgent", "get_memory_agent",
    "FinancialAgent", "get_financial_agent",
    "start_all_agents", "stop_all_agents", "get_all_agents",
]

# Track started agent instances for proper lifecycle management
_started_agents: list[BaseAgent] = []


def start_all_agents() -> list[BaseAgent]:
    """Initialize and start all agents."""
    global _started_agents
    agents = [
        get_coordinator(),
        ResearchAgent(),
        ValidatorAgent(),
        ExploitAgent(),
        DocumentationAgent(),
        get_strategy_agent(),
        get_memory_agent(),
        get_financial_agent(),
    ]
    for agent in agents:
        agent.start()
    _started_agents = agents
    logger.info("[AGENTS] All %d agents started", len(agents))
    return agents


def stop_all_agents() -> None:
    """Stop all running agents."""
    global _started_agents
    for agent in _started_agents:
        agent.stop()
    logger.info("[AGENTS] All agents stopped")
    _started_agents = []


def restart_all_agents() -> list[BaseAgent]:
    """Stop and restart all agents."""
    stop_all_agents()
    return start_all_agents()


def get_all_agents() -> list[BaseAgent]:
    if _started_agents:
        return _started_agents
    return [
        get_coordinator(),
        ResearchAgent(),
        ValidatorAgent(),
        ExploitAgent(),
        DocumentationAgent(),
        get_strategy_agent(),
        get_memory_agent(),
        get_financial_agent(),
    ]


def agents_health() -> dict:
    return {a.agent_id.value: a.health() for a in get_all_agents()}


def reset_all_agents() -> None:
    """Reset all agent singletons (for testing)."""
    stop_all_agents()
    import core_engines.agents.coordinator as _coord_mod
    if _coord_mod._COORDINATOR is not None:
        _coord_mod._COORDINATOR.stop()
        _coord_mod._COORDINATOR = None
    import core_engines.agents.strategy as _strat_mod
    _strat_mod._STRATEGY = None
    import core_engines.agents.memory as _mem_mod
    _mem_mod._MEMORY = None
    import core_engines.agents.financial as _fin_mod
    _fin_mod._FINANCIAL = None
    reset_agent_bus()
