import { Component, type ReactNode, type ErrorInfo } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class GlobalErrorBoundaryUI extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('GlobalErrorBoundaryUI caught:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback ?? <DefaultFallback />;
    }
    return this.props.children;
  }
}

function DefaultFallback() {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      minHeight: 200, padding: 32, textAlign: 'center', color: '#7c8299',
    }}>
      <div style={{ fontSize: 32, marginBottom: 12 }}>◈</div>
      <h2 style={{ margin: '0 0 4px', fontSize: 16, fontWeight: 600, color: '#e2e4e9' }}>
        Something went wrong
      </h2>
      <p style={{ margin: 0, fontSize: 13 }}>
        System encountered an unexpected state.
      </p>
      <button
        onClick={() => window.location.reload()}
        style={{
          marginTop: 16, padding: '8px 20px', borderRadius: 6, border: 'none',
          background: '#7c3aed', color: '#fff', fontSize: 13, fontWeight: 600,
          cursor: 'pointer', transition: 'background 0.15s',
        }}
        onMouseEnter={e => { e.currentTarget.style.background = '#6d28d9'; }}
        onMouseLeave={e => { e.currentTarget.style.background = '#7c3aed'; }}
      >
        Reload
      </button>
    </div>
  );
}

export function ApiErrorFallback({ message, onRetry }: { message?: string; onRetry?: () => void }) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      minHeight: 160, padding: 24, textAlign: 'center',
    }}>
      <div style={{
        padding: '14px 18px', borderRadius: 10, background: '#2a0f0f',
        border: '1px solid #ef4444', maxWidth: 400, width: '100%',
      }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: '#fca5a5', marginBottom: 4 }}>
          {message ?? 'Could not load data'}
        </div>
        <p style={{ margin: 0, fontSize: 11, color: '#ef444480' }}>
          System may be offline
        </p>
        {onRetry && (
          <button
            onClick={onRetry}
            style={{
              marginTop: 10, padding: '4px 14px', borderRadius: 4,
              background: 'transparent', border: '1px solid #ef4444',
              color: '#fca5a5', fontSize: 11, fontWeight: 600, cursor: 'pointer',
              transition: 'background 0.15s',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = '#ef444420'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
          >
            Retry
          </button>
        )}
      </div>
    </div>
  );
}
