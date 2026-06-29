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
  empty, emptyMessage = 'No data',
  loading, loadingComponent, style,
}: PanelProps) {
  const [collapsed, setCollapsed] = useState(defaultCollapsed);
  const toggle = useCallback(() => setCollapsed((c) => !c), []);

  return (
    <div style={{
      background: '#161B22', borderRadius: 14, border: '1px solid #212838',
      overflow: 'hidden', boxShadow: '0 1px 2px rgba(0,0,0,0.3)',
      transition: 'border-color 0.15s ease', ...style,
    }}>
      <div
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '16px 20px', borderBottom: '1px solid #212838',
          cursor: collapsible ? 'pointer' : undefined,
        }}
        onClick={collapsible ? toggle : undefined}
        onKeyDown={collapsible ? (e) => e.key === 'Enter' && toggle() : undefined}
        tabIndex={collapsible ? 0 : undefined}
        role={collapsible ? 'button' : undefined}
        aria-expanded={collapsible ? !collapsed : undefined}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2, flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {accent && (
              <div style={{ width: 3, height: 16, borderRadius: 2, background: accent, flexShrink: 0 }} />
            )}
            <span style={{ fontSize: 14, fontWeight: 600, color: '#F8FAFC' }}>{title}</span>
            {collapsible && (
              <span style={{
                fontSize: 10, color: '#6B7280', transition: 'transform 0.15s ease',
                transform: collapsed ? 'rotate(-90deg)' : 'rotate(0deg)',
              }}>
                ▼
              </span>
            )}
          </div>
          {subtitle && (
            <span style={{ fontSize: 11, color: '#6B7280' }}>{subtitle}</span>
          )}
        </div>
        {headerExtra && <div style={{ flexShrink: 0 }}>{headerExtra}</div>}
      </div>
      {!collapsed && (
        <div style={{ padding: 20, minHeight: loading ? 80 : undefined }}>
          {loading ? (
            loadingComponent || (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div style={{ height: 12, width: '80%', background: '#1F252E', borderRadius: 8, animation: 'shimmer 1.2s ease-in-out infinite' }} />
                <div style={{ height: 12, width: '60%', background: '#1F252E', borderRadius: 8, animation: 'shimmer 1.2s ease-in-out infinite' }} />
                <div style={{ height: 12, width: '70%', background: '#1F252E', borderRadius: 8, animation: 'shimmer 1.2s ease-in-out infinite' }} />
              </div>
            )
          ) : empty ? (
            <div style={{ textAlign: 'center', padding: '32px 0', color: '#6B7280', fontSize: 13, lineHeight: 1.6 }}>
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
