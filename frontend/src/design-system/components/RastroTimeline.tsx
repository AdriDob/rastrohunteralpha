import { tokens } from '../tokens';

export interface TimelineEvent {
  id: string;
  title: string;
  description?: string;
  timestamp?: string;
  status?: 'completed' | 'active' | 'pending' | 'failed';
  icon?: string;
  metadata?: Record<string, string>;
}

interface RastroTimelineProps {
  events: TimelineEvent[];
  activeId?: string;
}

const statusColors: Record<string, string> = {
  completed: tokens.colors.success,
  active: tokens.colors.primary,
  pending: tokens.colors.textFaint,
  failed: tokens.colors.error,
};

export function RastroTimeline({ events, activeId }: RastroTimelineProps) {
  return (
    <div style={{ position: 'relative', paddingLeft: tokens.spacing['3xl'] }}>
      {/* Vertical line */}
      <div style={{
        position: 'absolute', left: 9, top: 4, bottom: 4,
        width: 2, background: tokens.colors.border,
        borderRadius: 1,
      }} />

      {events.map((event, idx) => {
        const isActive = event.id === activeId;
        const dotColor = event.status
          ? statusColors[event.status]
          : tokens.colors.textFaint;

        return (
          <div
            key={event.id}
            style={{
              position: 'relative',
              paddingBottom: idx < events.length - 1 ? tokens.spacing.xl : 0,
              opacity: event.status === 'pending' ? 0.5 : 1,
            }}
          >
            {/* Dot */}
            <div style={{
              position: 'absolute',
              left: `-${tokens.spacing['3xl']}`,
              top: 4,
              width: 12,
              height: 12,
              borderRadius: '50%',
              background: dotColor,
              border: `2px solid ${tokens.colors.surface}`,
              boxShadow: isActive ? `0 0 0 4px ${dotColor}33` : undefined,
              transition: `all ${tokens.animation.normal}`,
            }} />

            {/* Content */}
            <div style={{
              background: isActive ? tokens.colors.hover : 'transparent',
              borderRadius: tokens.radius.md,
              padding: isActive ? tokens.spacing.md : `${tokens.spacing.sm} 0`,
              transition: `all ${tokens.animation.normal}`,
            }}>
              <div style={{
                display: 'flex', alignItems: 'center', gap: tokens.spacing.sm,
              }}>
                {event.icon && <span>{event.icon}</span>}
                <span style={{
                  fontSize: tokens.typography.sizes.sm,
                  fontWeight: tokens.typography.weights.semibold,
                  color: tokens.colors.text,
                }}>
                  {event.title}
                </span>
                {event.timestamp && (
                  <span style={{
                    fontSize: tokens.typography.sizes.xs,
                    color: tokens.colors.textFaint,
                    marginLeft: 'auto',
                  }}>
                    {event.timestamp}
                  </span>
                )}
              </div>

              {event.description && (
                <div style={{
                  fontSize: tokens.typography.sizes.sm,
                  color: tokens.colors.textMuted,
                  marginTop: tokens.spacing.xs,
                  lineHeight: 1.4,
                }}>
                  {event.description}
                </div>
              )}

              {event.metadata && Object.keys(event.metadata).length > 0 && (
                <div style={{
                  display: 'flex', flexWrap: 'wrap', gap: tokens.spacing.sm,
                  marginTop: tokens.spacing.sm,
                }}>
                  {Object.entries(event.metadata).map(([k, v]) => (
                    <span key={k} style={{
                      fontSize: tokens.typography.sizes.xs,
                      color: tokens.colors.textFaint,
                      background: tokens.colors.surface,
                      padding: `2px ${tokens.spacing.sm}`,
                      borderRadius: tokens.radius.sm,
                    }}>
                      {k}: {v}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
