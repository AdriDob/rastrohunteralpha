import { useState, useCallback } from 'react';

interface PanelProps {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  collapsible?: boolean;
  defaultCollapsed?: boolean;
  accent?: string;
  headerExtra?: React.ReactNode;
  empty?: boolean;
  emptyMessage?: string;
  loading?: boolean;
  loadingComponent?: React.ReactNode;
  style?: React.CSSProperties;
}

export default function Panel({
  title, subtitle, children, collapsible = false,
  defaultCollapsed = false, accent, headerExtra,
  empty, emptyMessage = 'No data available',
  loading, loadingComponent, style,
}: PanelProps) {
  const [collapsed, setCollapsed] = useState(defaultCollapsed);
  const toggle = useCallback(() => setCollapsed((c) => !c), []);

  return (
    <div style={{
      background: '#1a1d29', borderRadius: 10, border: '1px solid #2a2e3d',
      overflow: 'hidden', transition: 'border-color 0.15s ease', ...style,
    }}>
      <div
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '14px 20px', borderBottom: '1px solid #2a2e3d',
          cursor: collapsible ? 'pointer' : undefined,
          transition: 'background 0.15s ease',
        }}
        onClick={collapsible ? toggle : undefined}
        onKeyDown={collapsible ? (e) => e.key === 'Enter' && toggle() : undefined}
        tabIndex={collapsible ? 0 : undefined}
        role={collapsible ? 'button' : undefined}
        aria-expanded={collapsible ? !collapsed : undefined}
        onMouseEnter={e => { if (collapsible) e.currentTarget.style.background = '#1e2230'; }}
        onMouseLeave={e => { if (collapsible) e.currentTarget.style.background = 'transparent'; }}
        onMouseDown={e => { if (collapsible) e.currentTarget.style.background = '#252836'; }}
        onMouseUp={e => { if (collapsible) e.currentTarget.style.background = '#1e2230'; }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {accent && (
              <div style={{ width: 3, height: 16, borderRadius: 2, background: accent, flexShrink: 0 }} />
            )}
            <span style={{ fontSize: 14, fontWeight: 600, color: '#e2e4e9' }}>{title}</span>
            {collapsible && (
              <span style={{
                fontSize: 10, color: '#7c8299', transition: 'transform 0.15s ease, color 0.15s ease',
                transform: collapsed ? 'rotate(-90deg)' : 'rotate(0deg)',
              }}>
                ▼
              </span>
            )}
          </div>
          {subtitle && (
            <span style={{ fontSize: 11, color: '#7c8299' }}>{subtitle}</span>
          )}
        </div>
        {headerExtra && <div>{headerExtra}</div>}
      </div>
      {!collapsed && (
        <div style={{ padding: 20, minHeight: loading ? 80 : undefined, transition: 'opacity 0.15s ease' }}>
          {loading ? (
            loadingComponent || (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div style={{ height: 12, width: '80%', background: '#2a2e3d', borderRadius: 4, animation: 'shimmer 1.5s ease-in-out infinite' }} />
                <div style={{ height: 12, width: '60%', background: '#2a2e3d', borderRadius: 4, animation: 'shimmer 1.5s ease-in-out infinite' }} />
                <div style={{ height: 12, width: '70%', background: '#2a2e3d', borderRadius: 4, animation: 'shimmer 1.5s ease-in-out infinite' }} />
              </div>
            )
          ) : empty ? (
            <div style={{ textAlign: 'center', padding: '24px 0', color: '#7c8299', fontSize: 13 }}>
              {emptyMessage}
            </div>
          ) : (
            children
          )}
        </div>
      )}
    </div>
  );
}
