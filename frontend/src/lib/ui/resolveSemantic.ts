// ─────────────────────────────────────────────────────────────────────
// RASTRO — Semantic Resolver Functions
//
// Pure deterministic functions that map raw data values to semantic
// visual contracts. No component should resolve meaning directly.
// ─────────────────────────────────────────────────────────────────────

import {
  type SemanticVisual,
  type RiskLevel,
  type SystemState,
  type ActionType,
  type IntelligenceSignal,
  type PriorityLevel,
  getSemantic,
  isKnownSemantic,
  semanticRegistry,
} from './semantic';

// ─── Dev-mode violation tracker ─────────────────────────────────────

const violations = new Set<string>();

function logViolation(msg: string): void {
  if (import.meta.env.DEV && !violations.has(msg)) {
    violations.add(msg);
    console.warn(`[Semantic] ${msg}`);
  }
}

// ─── Helpers ─────────────────────────────────────────────────────────

function resolveFromRegistry(key: string, fallback: SemanticVisual): SemanticVisual {
  if (isKnownSemantic(key)) return getSemantic(key) as SemanticVisual;
  logViolation(`Unknown semantic key "${key}" — using fallback`);
  return fallback;
}

// ─── RISK Resolver ───────────────────────────────────────────────────

const riskTextMap: Record<string, RiskLevel> = {
  critical: 'critical',
  high: 'high',
  medium: 'medium',
  low: 'low',
  info: 'info',
};

export function resolveRisk(risk: string): SemanticVisual {
  const key = riskTextMap[risk.toLowerCase()];
  if (key) return semanticRegistry[key];
  logViolation(`Unmapped risk text "${risk}" — using info fallback`);
  return semanticRegistry.info;
}

// ─── SYSTEM STATE Resolver ───────────────────────────────────────────

const stateTextMap: Record<string, SystemState> = {
  healthy: 'healthy',
  degraded: 'degraded',
  warning: 'warning',
  failing: 'failing',
  error: 'failing',
  unhealthy: 'degraded',
};

export function resolveSystemState(state: string): SemanticVisual {
  const key = stateTextMap[state.toLowerCase()];
  if (key) return semanticRegistry[key];
  logViolation(`Unmapped system state "${state}" — using info fallback`);
  return semanticRegistry.info;
}

// ─── ACTION TYPE Resolver ────────────────────────────────────────────

const actionTextMap: Record<string, ActionType> = {
  primary: 'primary_action',
  primary_action: 'primary_action',
  secondary: 'secondary_action',
  secondary_action: 'secondary_action',
  suggested: 'suggested_action',
  suggested_action: 'suggested_action',
  suppressed: 'suppressed_action',
  suppressed_action: 'suppressed_action',
};

export function resolveActionType(action: string): SemanticVisual {
  const key = actionTextMap[action.toLowerCase()];
  if (key) return semanticRegistry[key];
  logViolation(`Unmapped action type "${action}" — using secondary fallback`);
  return semanticRegistry.secondary_action;
}

// ─── INTELLIGENCE SIGNAL Resolver ────────────────────────────────────

const signalTextMap: Record<string, IntelligenceSignal> = {
  opportunity: 'opportunity',
  insight: 'insight',
  anomaly: 'anomaly',
  trend: 'trend',
};

export function resolveIntelligenceSignal(signal: string): SemanticVisual {
  const key = signalTextMap[signal.toLowerCase()];
  if (key) return semanticRegistry[key];
  logViolation(`Unmapped intelligence signal "${signal}" — using insight fallback`);
  return semanticRegistry.insight;
}

// ─── PRIORITY Resolver ───────────────────────────────────────────────

const priorityMap: Record<string, PriorityLevel> = {
  p0: 'p0',
  urgent: 'p0',
  p1: 'p1',
  high: 'p1',
  p2: 'p2',
  medium: 'p2',
  p3: 'p3',
  low: 'p3',
  background: 'p3',
};

export function resolvePriority(priority: string | number): SemanticVisual {
  if (typeof priority === 'number') {
    if (priority >= 0.9) return semanticRegistry.p0;
    if (priority >= 0.7) return semanticRegistry.p1;
    if (priority >= 0.4) return semanticRegistry.p2;
    return semanticRegistry.p3;
  }
  const key = priorityMap[priority.toLowerCase()];
  if (key) return semanticRegistry[key];
  logViolation(`Unmapped priority "${priority}" — using p3 fallback`);
  return semanticRegistry.p3;
}

// ─── OUTCOME SCORE Resolver ──────────────────────────────────────────

export function resolveOutcomeScore(score: number): SemanticVisual {
  if (score > 0.7) return semanticRegistry.healthy;
  if (score > 0.3) return semanticRegistry.warning;
  return semanticRegistry.failing;
}

// ─── GENERIC Resolver ────────────────────────────────────────────────

export function resolveSemantic(key: string): SemanticVisual {
  return resolveFromRegistry(key, semanticRegistry.info);
}

// ─── Semantic alias map (re-exports from Badge) ──────────────────────

export const aliasCanonicalMap: Record<string, string> = {
  success: 'severity',
  warning: 'severity',
  error: 'severity',
};

export const aliasColorMap: Record<string, string> = {
  success: '#22c55e',
  warning: '#eab308',
  error: '#ef4444',
};

// ─── Badge variant normalization (shared with Badge.tsx) ─────────────

const warned = new Set<string>();
export function normalizeVariant(variant: string): { canonicalVariant: string; aliasColor?: string } {
  const canonical = aliasCanonicalMap[variant];
  if (canonical) {
    if (import.meta.env.DEV && !warned.has(variant)) {
      warned.add(variant);
      console.warn(
        `[Badge] variant="${variant}" is deprecated. Use variant="severity" with the appropriate severity text instead.`,
      );
    }
    return { canonicalVariant: canonical, aliasColor: aliasColorMap[variant] };
  }
  return { canonicalVariant: variant };
}
