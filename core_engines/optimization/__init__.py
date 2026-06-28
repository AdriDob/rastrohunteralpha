"""Optimization — auto-tuning of system parameters based on runtime metrics."""

from __future__ import annotations

from core_engines.optimization.engine import (
    AutoOptimizationEngine,
    OptimizationAction,
    get_optimization_engine,
    reset_optimization_engine,
)

__all__ = [
    "AutoOptimizationEngine", "OptimizationAction",
    "get_optimization_engine", "reset_optimization_engine",
]
