import { tokens } from '../tokens';

interface RastroBadgeProps {
  label: string;
  severity?: 'info' | 'success' | 'warning' | 'error' | 'accent' | 'neutral';
  size?: 'sm' | 'md';
}

const severityColors: Record<string, { bg: string; text: string }> = {
  info: { bg: 'rgba(59,130,246,0.12)', text: tokens.colors.primary },
  success: { bg: 'rgba(34,197,94,0.12)', text: tokens.colors.success },
  warning: { bg: 'rgba(245,158,11,0.12)', text: tokens.colors.warning },
  error: { bg: 'rgba(239,68,68,0.12)', text: tokens.colors.error },
  accent: { bg: tokens.colors.accentGlow, text: tokens.colors.accent },
  neutral: { bg: tokens.colors.hover, text: tokens.colors.textMuted },
};

export function RastroBadge({ label, severity = 'neutral', size = 'sm' }: RastroBadgeProps) {
  const colors = severityColors[severity];
  const fontSize = size === 'sm' ? tokens.typography.sizes.xs : tokens.typography.sizes.sm;
  const padding = size === 'sm'
    ? `${tokens.spacing.xs} ${tokens.spacing.md}`
    : `${tokens.spacing.sm} ${tokens.spacing.lg}`;
  const pillRadius = '999px';

  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      background: colors.bg,
      color: colors.text,
      fontSize,
      fontWeight: tokens.typography.weights.medium,
      padding,
      borderRadius: pillRadius,
      lineHeight: 1,
      whiteSpace: 'nowrap',
    }}>
      {label}
    </span>
  );
}
