import { useState, useEffect } from 'react';

const API = '/api';

async function checkLicense(): Promise<{ valid: boolean; activated: boolean }> {
  const resp = await fetch(`${API}/license/status`);
  const body = await resp.json();
  return { valid: body.data?.valid ?? false, activated: body.data?.activated ?? false };
}

async function activateLicense(key: string): Promise<{ ok: boolean; error?: string }> {
  const resp = await fetch(`${API}/license/activate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ key }),
  });
  const body = await resp.json();
  if (body.error) return { ok: false, error: body.error };
  return { ok: true };
}

export default function Activation() {
  const [key, setKey] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [checking, setChecking] = useState(true);
  const [activated, setActivated] = useState(false);

  useEffect(() => {
    checkLicense().then((s) => {
      if (s.valid) {
        setActivated(true);
        setTimeout(() => { window.location.href = '/'; }, 1500);
      }
      setChecking(false);
    }).catch(() => {
      setChecking(false);
    });
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!key.trim()) { setError('Please enter a license key'); return; }
    setLoading(true);
    try {
      const result = await activateLicense(key.trim());
      setLoading(false);
      if (result.ok) {
        setActivated(true);
        window.location.href = '/';
      } else {
        setError(result.error || 'Activation failed');
      }
    } catch {
      setLoading(false);
      setError('Network error. Please try again.');
    }
  };

  if (checking) {
    return (
      <div style={styles.container}>
        <div style={{ color: '#7c8299', fontSize: 14 }}>Checking license...</div>
      </div>
    );
  }

  if (activated) {
    return (
      <div style={styles.container}>
        <div style={styles.card}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>✓</div>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: '#e0e0e0', margin: 0 }}>License Active</h1>
          <p style={{ color: '#7c8299', fontSize: 14, margin: '12px 0' }}>
            Rastro is ready to use.
          </p>
          <button
            onClick={() => window.location.href = '/'}
            style={styles.button}
          >
            Go to Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <div style={{ fontSize: 36, fontWeight: 800, letterSpacing: '-0.03em', color: '#fff', marginBottom: 8 }}>
          <span style={{ color: '#7c3aed' }}>R</span>astro
        </div>
        <p style={{ color: '#7c8299', fontSize: 14, margin: '0 0 24px' }}>
          Activate your license to continue
        </p>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12, width: '100%' }}>
          <input
            type="text"
            placeholder="XXXXX-XXXXX-XXXXX-XXXXX-XXXXX"
            value={key}
            onChange={(e) => setKey(e.target.value.toUpperCase())}
            style={styles.input}
            disabled={loading}
          />
          {error && (
            <div style={{ color: '#ef4444', fontSize: 13, textAlign: 'center' }}>{error}</div>
          )}
          <button
            type="submit"
            disabled={loading}
            style={{
              ...styles.button,
              opacity: loading ? 0.6 : 1,
            }}
          >
            {loading ? 'Activating...' : 'Activate'}
          </button>
        </form>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    position: 'fixed', inset: 0, zIndex: 9999,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    background: '#13151d',
  },
  card: {
    display: 'flex', flexDirection: 'column', alignItems: 'center',
    padding: '48px 40px', borderRadius: 16,
    background: '#1a1d2e', border: '1px solid #2a2e3d',
    maxWidth: 400, width: '90%',
  },
  input: {
    width: '100%', padding: '12px 16px', borderRadius: 8,
    border: '1px solid #2a2e3d', background: '#13151d',
    color: '#e0e0e0', fontSize: 16, fontFamily: 'monospace',
    textAlign: 'center', letterSpacing: '0.05em',
    outline: 'none', boxSizing: 'border-box',
  },
  button: {
    width: '100%', padding: '12px 24px', borderRadius: 8,
    border: 'none', background: '#7c3aed', color: '#fff',
    fontSize: 14, fontWeight: 600, cursor: 'pointer',
  },
};
