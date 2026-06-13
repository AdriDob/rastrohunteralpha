import { Skeleton } from './Skeleton';

interface LoadingStateProps {
  count?: number;
  type?: 'card' | 'list' | 'detail';
}

export default function LoadingState({ count = 3, type = 'card' }: LoadingStateProps) {
  if (type === 'list') {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '12px 16px', borderRadius: 10, border: '1px solid #2a2e3d',
            background: '#1a1d29',
          }}>
            <div>
              <Skeleton width={140} height={14} />
              <Skeleton width={80} height={10} style={{ marginTop: 6 }} />
            </div>
            <Skeleton width={70} height={28} borderRadius={6} />
          </div>
        ))}
      </div>
    );
  }

  if (type === 'detail') {
    return (
      <div style={{
        borderRadius: 14, border: '1px solid #2a2e3d', padding: 20,
        background: '#1a1d29',
      }}>
        <Skeleton width={80} height={12} />
        <Skeleton width="80%" height={22} style={{ marginTop: 12 }} />
        <Skeleton width="60%" height={12} style={{ marginTop: 8 }} />
        <Skeleton width={100} height={30} style={{ marginTop: 14 }} />
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} style={{
          borderRadius: 10, border: '1px solid #2a2e3d', padding: 14,
          background: '#1a1d29',
        }}>
          <Skeleton width="70%" height={14} />
          <Skeleton width="50%" height={10} style={{ marginTop: 8 }} />
        </div>
      ))}
    </div>
  );
}
