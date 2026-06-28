import { useEffect, useRef, useState } from 'react';
import { tokens } from '../tokens';

interface RastroKPICardProps {
  label: string;
  value: string | number;
  prefix?: string;
  suffix?: string;
  trend?: { value: number; direction: 'up' | 'down' | 'neutral' };
  icon?: string;
  accent?: 'primary' | 'accent' | 'success' | 'warning' | 'error';
  animate?: boolean;
  onClick?: () => void;
}

function AnimatedNumber({ value, duration = 800 }: { value: number; duration?: number }) {
  const [display, setDisplay] = useState(0);
  const ref = useRef<number>(0);

  useEffect(() => {
    const start = ref.current;
    const end = value;
    const startTime = performance.now();

    function tick(now: number) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = start + (end - start) * eased;
      setDisplay(current);
      if (progress < 1) requestAnimationFrame(tick);
      else ref.current = end;
    }

    requestAnimationFrame(tick);
  }, [value, duration]);

  return <>{Math.round(display)}</>;
}

export function RastroKPICard({
  label, value, prefix, suffix, trend, icon,
  accent = 'primary', animate = false, onClick,
}: RastroKPICardProps) {
  const accentColors: Record<string, string> = {
    primary: tokens.colors.primary,
    accent: tokens.colors.accent,
    success: tokens.colors.success,
    warning: tokens.colors.warning,
    error: tokens.colors.error,
  };

  const trendIcons: Record<string, string> = {
    up: '\u2191', down: '\u2193', neutral: '\u2192',
  };

  const trendColors: Record<string, string> = {
    up: tokens.colors.success,
    down: tokens.colors.error,
    neutral: tokens.colors.textMuted,
  };

  return (
    <div
      onClick={onClick}
      style={{
        background: tokens.colors.card,
        border: `1px solid ${tokens.colors.border}`,
        borderRadius: tokens.radius.xl,
        padding: tokens.spacing.xl,
        display: 'flex',
        flexDirection: 'column',
        gap: tokens.spacing.sm,
        cursor: onClick ? 'pointer' : undefined,
        transition: `all ${tokens.animation.normal}`,
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Accent line */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0,
        height: 2, background: accentColors[accent],
        opacity: 0.8,
      }} />

      <div style={{
        display: 'flex', alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <span style={{
          fontSize: tokens.typography.sizes.sm,
          color: tokens.colors.textMuted,
          fontWeight: tokens.typography.weights.medium,
          textTransform: 'uppercase',
          letterSpacing: '0.5px',
        }}>
          {label}
        </span>
        {icon && <span style={{ fontSize: 18, opacity: 0.5 }}>{icon}</span>}
      </div>

      <div style={{
        display: 'flex', alignItems: 'baseline', gap: tokens.spacing.sm,
      }}>
        {prefix && (
          <span style={{
            fontSize: tokens.typography.sizes.lg,
            color: tokens.colors.textSecondary,
            fontWeight: tokens.typography.weights.medium,
          }}>
            {prefix}
          </span>
        )}
        <span style={{
          fontSize: tokens.typography.sizes['2xl'],
          fontWeight: tokens.typography.weights.bold,
          color: tokens.colors.text,
          fontFamily: tokens.typography.mono,
          lineHeight: 1.1,
        }}>
          {animate && typeof value === 'number'
            ? <AnimatedNumber value={value} />
            : value}
        </span>
        {suffix && (
          <span style={{
            fontSize: tokens.typography.sizes.sm,
            color: tokens.colors.textMuted,
          }}>
            {suffix}
          </span>
        )}
      </div>

      {trend && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: tokens.spacing.xs,
          fontSize: tokens.typography.sizes.sm,
          color: trendColors[trend.direction],
        }}>
          <span>{trendIcons[trend.direction]}</span>
          <span>{Math.abs(trend.value)}%</span>
          <span style={{ color: tokens.colors.textFaint }}>
            vs. periodo anterior
          </span>
        </div>
      )}
    </div>
  );
}
