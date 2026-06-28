import React from 'react';
import { tokens } from '../tokens';

interface RastroCardProps {
  title?: string;
  subtitle?: string;
  icon?: string;
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
  hoverable?: boolean;
  accent?: 'primary' | 'accent' | 'success' | 'warning' | 'error' | 'none';
  padding?: keyof typeof tokens.spacing;
}

export function RastroCard({
  title, subtitle, icon, children, className = '', onClick,
  hoverable, accent = 'none', padding = 'xl',
}: RastroCardProps) {
  const accentColors: Record<string, string> = {
    primary: tokens.colors.primary,
    accent: tokens.colors.accent,
    success: tokens.colors.success,
    warning: tokens.colors.warning,
    error: tokens.colors.error,
  };

  return (
    <div
      onClick={onClick}
      className={className}
      style={{
        background: tokens.colors.card,
        border: `1px solid ${tokens.colors.border}`,
        borderRadius: tokens.radius.xl,
        padding: tokens.spacing[padding],
        position: 'relative',
        overflow: 'hidden',
        cursor: onClick ? 'pointer' : undefined,
        transition: `all ${tokens.animation.normal}`,
        borderTop: accent !== 'none' ? `2px solid ${accentColors[accent]}` : undefined,
        ...(hoverable ? {
          ':hover': {
            borderColor: tokens.colors.borderHover,
            boxShadow: tokens.shadow.elevated,
          },
        } : {}),
      }}
    >
      {(title || icon) && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: tokens.spacing.md,
          marginBottom: tokens.spacing.xl,
        }}>
          {icon && <span style={{ fontSize: 18 }}>{icon}</span>}
          <div style={{ flex: 1 }}>
            {title && (
              <div style={{
                fontSize: tokens.typography.sizes.md,
                fontWeight: tokens.typography.weights.semibold,
                color: tokens.colors.text,
              }}>
                {title}
              </div>
            )}
            {subtitle && (
              <div style={{
                fontSize: tokens.typography.sizes.sm,
                color: tokens.colors.textMuted,
                marginTop: tokens.spacing.xs,
              }}>
                {subtitle}
              </div>
            )}
          </div>
        </div>
      )}
      {children}
    </div>
  );
}
