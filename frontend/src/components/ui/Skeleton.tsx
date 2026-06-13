const shimmer = `
  @keyframes shimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
  }
`;

const styleId = 'skeleton-shimmer';
if (typeof document !== 'undefined' && !document.getElementById(styleId)) {
  const el = document.createElement('style');
  el.id = styleId;
  el.textContent = shimmer;
  document.head.appendChild(el);
}

interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  borderRadius?: string | number;
  style?: React.CSSProperties;
}

export function Skeleton({ width = '100%', height = 16, borderRadius = 6, style }: SkeletonProps) {
  return (
    <div
      style={{
        width, height, borderRadius,
        background: 'linear-gradient(90deg, #1e2230 25%, #2a2e3d 50%, #1e2230 75%)',
        backgroundSize: '200% 100%',
        animation: 'shimmer 1.5s ease-in-out infinite',
        ...style,
      }}
    />
  );
}

export function SkeletonCard() {
  return (
    <div style={{
      background: '#1e2230', borderRadius: 8, border: '1px solid #2a2e3d',
      padding: 20, display: 'flex', flexDirection: 'column', gap: 12,
    }}>
      <Skeleton width={80} height={12} />
      <Skeleton width={120} height={28} />
      <Skeleton width="60%" height={10} />
    </div>
  );
}

export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} height={36} style={{ opacity: 1 - i * 0.12 }} />
      ))}
    </div>
  );
}

export function SkeletonPanel() {
  return (
    <div style={{
      background: '#1e2230', borderRadius: 8, border: '1px solid #2a2e3d',
      padding: 20,
    }}>
      <Skeleton width={140} height={14} style={{ marginBottom: 16 }} />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <Skeleton height={12} width="90%" />
        <Skeleton height={12} width="70%" />
        <Skeleton height={12} width="80%" />
      </div>
    </div>
  );
}
