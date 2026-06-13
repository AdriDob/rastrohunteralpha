// ─────────────────────────────────────────────────────────────────────
// RASTRO — Canonical UI Semantic Taxonomy
//
// Every visual element in Rastro maps to one of these semantic values.
// No component decides meaning. All meaning comes from the intelligence
// layer, priority engine, or system state engine.
//
// This file is the single source of truth for UI semantics.
// ─────────────────────────────────────────────────────────────────────

// ─── Category Types ──────────────────────────────────────────────────

export type RiskLevel = 'critical' | 'high' | 'medium' | 'low' | 'info';

export type SystemState = 'healthy' | 'degraded' | 'warning' | 'failing';

export type ActionType =
  | 'primary_action'
  | 'secondary_action'
  | 'suggested_action'
  | 'suppressed_action';

export type IntelligenceSignal =
  | 'opportunity'
  | 'insight'
  | 'anomaly'
  | 'trend';

export type PriorityLevel = 'p0' | 'p1' | 'p2' | 'p3';

export type BadgeSemantic = 'default' | 'severity' | 'tier' | 'stage';

// ─── Visual Contract ─────────────────────────────────────────────────

export interface SemanticVisual {
  color: string;
  badgeVariant: BadgeSemantic;
  label: string;
  animatable: boolean;
  emphasis: 'low' | 'medium' | 'high' | 'highest';
  collapsible: boolean;
}

// ─── Semantic Registry ───────────────────────────────────────────────

type SemanticKey = RiskLevel | SystemState | ActionType | IntelligenceSignal | PriorityLevel;

export const semanticRegistry: Record<SemanticKey, SemanticVisual> = {
  // ── RISK ──────────────────────────────────────────────────────────
  critical: {
    color: '#ef4444',
    badgeVariant: 'severity',
    label: 'Critical',
    animatable: true,
    emphasis: 'highest',
    collapsible: false,
  },
  high: {
    color: '#f97316',
    badgeVariant: 'severity',
    label: 'High',
    animatable: true,
    emphasis: 'high',
    collapsible: false,
  },
  medium: {
    color: '#eab308',
    badgeVariant: 'severity',
    label: 'Medium',
    animatable: false,
    emphasis: 'medium',
    collapsible: false,
  },
  low: {
    color: '#3b82f6',
    badgeVariant: 'severity',
    label: 'Low',
    animatable: false,
    emphasis: 'low',
    collapsible: true,
  },
  info: {
    color: '#6b7280',
    badgeVariant: 'severity',
    label: 'Info',
    animatable: false,
    emphasis: 'low',
    collapsible: true,
  },

  // ── SYSTEM STATE ──────────────────────────────────────────────────
  healthy: {
    color: '#22c55e',
    badgeVariant: 'severity',
    label: 'Healthy',
    animatable: false,
    emphasis: 'low',
    collapsible: true,
  },
  degraded: {
    color: '#f59e0b',
    badgeVariant: 'severity',
    label: 'Degraded',
    animatable: false,
    emphasis: 'medium',
    collapsible: false,
  },
  warning: {
    color: '#f97316',
    badgeVariant: 'severity',
    label: 'Warning',
    animatable: true,
    emphasis: 'high',
    collapsible: false,
  },
  failing: {
    color: '#ef4444',
    badgeVariant: 'severity',
    label: 'Failing',
    animatable: true,
    emphasis: 'highest',
    collapsible: false,
  },

  // ── ACTION ────────────────────────────────────────────────────────
  primary_action: {
    color: '#7c3aed',
    badgeVariant: 'default',
    label: 'Primary',
    animatable: true,
    emphasis: 'high',
    collapsible: false,
  },
  secondary_action: {
    color: '#6b7280',
    badgeVariant: 'default',
    label: 'Secondary',
    animatable: false,
    emphasis: 'low',
    collapsible: true,
  },
  suggested_action: {
    color: '#22c55e',
    badgeVariant: 'default',
    label: 'Suggested',
    animatable: true,
    emphasis: 'medium',
    collapsible: false,
  },
  suppressed_action: {
    color: '#4a4f63',
    badgeVariant: 'default',
    label: 'Suppressed',
    animatable: false,
    emphasis: 'low',
    collapsible: true,
  },

  // ── INTELLIGENCE SIGNAL ───────────────────────────────────────────
  opportunity: {
    color: '#22c55e',
    badgeVariant: 'default',
    label: 'Opportunity',
    animatable: true,
    emphasis: 'high',
    collapsible: false,
  },
  insight: {
    color: '#3b82f6',
    badgeVariant: 'default',
    label: 'Insight',
    animatable: false,
    emphasis: 'medium',
    collapsible: false,
  },
  anomaly: {
    color: '#f97316',
    badgeVariant: 'severity',
    label: 'Anomaly',
    animatable: true,
    emphasis: 'high',
    collapsible: false,
  },
  trend: {
    color: '#8b5cf6',
    badgeVariant: 'default',
    label: 'Trend',
    animatable: false,
    emphasis: 'low',
    collapsible: true,
  },

  // ── PRIORITY ──────────────────────────────────────────────────────
  p0: {
    color: '#ef4444',
    badgeVariant: 'severity',
    label: 'P0 — Urgent',
    animatable: true,
    emphasis: 'highest',
    collapsible: false,
  },
  p1: {
    color: '#f97316',
    badgeVariant: 'severity',
    label: 'P1 — High',
    animatable: true,
    emphasis: 'high',
    collapsible: false,
  },
  p2: {
    color: '#eab308',
    badgeVariant: 'severity',
    label: 'P2 — Medium',
    animatable: false,
    emphasis: 'medium',
    collapsible: false,
  },
  p3: {
    color: '#6b7280',
    badgeVariant: 'severity',
    label: 'P3 — Background',
    animatable: false,
    emphasis: 'low',
    collapsible: true,
  },
};

// ─── Category Metadata ──────────────────────────────────────────────

export interface SemanticCategory {
  id: string;
  label: string;
  values: string[];
}

export const semanticCategories: SemanticCategory[] = [
  { id: 'risk', label: 'Risk', values: ['critical', 'high', 'medium', 'low', 'info'] },
  { id: 'system_state', label: 'System State', values: ['healthy', 'degraded', 'warning', 'failing'] },
  { id: 'action', label: 'Action', values: ['primary_action', 'secondary_action', 'suggested_action', 'suppressed_action'] },
  { id: 'intelligence_signal', label: 'Intelligence Signal', values: ['opportunity', 'insight', 'anomaly', 'trend'] },
  { id: 'priority', label: 'Priority', values: ['p0', 'p1', 'p2', 'p3'] },
];

// ─── Helpers ─────────────────────────────────────────────────────────

export function getSemantic(key: string): SemanticVisual | undefined {
  return semanticRegistry[key as SemanticKey];
}

export function isKnownSemantic(key: string): boolean {
  return key in semanticRegistry;
}
