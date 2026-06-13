import type { SemanticVisual } from '../../lib/ui/semantic';
import { normalizeVariant } from '../../lib/ui/resolveSemantic';

const severityColors: Record<string, string> = {
  critical: '#ef4444',
  high: '#f97316',
  medium: '#eab308',
  low: '#3b82f6',
  info: '#6b7280',
};

const tierColors: Record<string, string> = {
  HIGH_CONFIDENCE: '#22c55e',
  MEDIUM_CONFIDENCE: '#eab308',
  LOW_CONFIDENCE: '#ef4444',
};

const stageColors: Record<string, string> = {
  recon: '#8b5cf6',
  endpoint_discovered: '#3b82f6',
  verdict_assigned: '#f97316',
  evidence_generated: '#22c55e',
  report_generated: '#ef4444',
  finding_created: '#eab308',
};

type BadgeVariant = 'default' | 'severity' | 'tier' | 'stage';
/** @deprecated Use canonical BadgeVariant instead */
type DeprecatedBadgeVariant = 'success' | 'warning' | 'error';

interface BadgeProps {
  text?: string;
  children?: React.ReactNode;
  /** @deprecated success/warning/error are aliases for severity canonical. Use variant="severity" instead. */
  variant?: BadgeVariant | DeprecatedBadgeVariant;
  color?: string;
  size?: 'sm' | 'md';
  /** When provided, uses semantic visual contract directly — skips variant-based resolution. */
  semantic?: SemanticVisual;
}

function resolveColor(text: string, variant: string, clr?: string): string {
  if (clr) return clr;
  const { canonicalVariant, aliasColor } = normalizeVariant(variant);
  if (aliasColor) return aliasColor;
  if (canonicalVariant === 'severity') return severityColors[text.toLowerCase()] || '#6b7280';
  if (canonicalVariant === 'tier') return tierColors[text] || '#6b7280';
  if (canonicalVariant === 'stage') return stageColors[text] || '#6b7280';
  return '#6b7280';
}

export default function Badge({ text, children, variant = 'default', color, size = 'sm', semantic }: BadgeProps) {
  const resolvedColor = semantic
    ? semantic.color
    : resolveColor(text || '', variant, color);

  return (
    <span
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 4,
        padding: size === 'sm' ? '2px 8px' : '4px 12px',
        borderRadius: 999, fontSize: size === 'sm' ? 10 : 12,
        fontWeight: 600, letterSpacing: 0.3,
        background: `${resolvedColor}18`,
        color: resolvedColor,
        border: `1px solid ${resolvedColor}30`,
        textTransform: 'uppercase',
        whiteSpace: 'nowrap',
      }}
    >
      {children ?? text}
    </span>
  );
}
