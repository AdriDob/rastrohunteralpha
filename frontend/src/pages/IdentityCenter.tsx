import { useCallback, useEffect, useState } from 'react';
import { useI18n } from '../lib/i18n';
import {
  getIdentityCenter,
  connectPlatform,
  disconnectPlatform,
  setPlatformMode,
  removePlatform,
  setEmail,
  setWallets,
  setNeverSubmit,
  type IdentityCenterData,
} from '../lib/api';

const cardStyle: React.CSSProperties = {
  background: '#1a1d29', borderRadius: 10, padding: 24,
  border: '1px solid #2a2e3d',
};

const labelStyle: React.CSSProperties = {
  fontSize: 11, fontWeight: 700, color: '#7c8299',
  textTransform: 'uppercase', letterSpacing: 1, marginBottom: 16,
};

const rowStyle: React.CSSProperties = {
  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
  padding: '12px 0', borderBottom: '1px solid #1a1d29',
};

const inputStyle: React.CSSProperties = {
  width: '100%', padding: '8px 12px', borderRadius: 6,
  border: '1px solid #2a2e3d', background: '#11131f', color: '#e0e0e0',
  fontSize: 13, outline: 'none', boxSizing: 'border-box',
  marginTop: 4,
};

const btnStyle: React.CSSProperties = {
  padding: '8px 20px', borderRadius: 6, border: 'none',
  background: '#7c3aed', color: '#fff', fontSize: 13, fontWeight: 600,
  cursor: 'pointer',
};

const badgeConnected: React.CSSProperties = {
  padding: '3px 10px', borderRadius: 10, fontSize: 11, fontWeight: 600,
  background: 'rgba(34,197,94,0.15)', color: '#22c55e',
};

const badgeDisconnected: React.CSSProperties = {
  padding: '3px 10px', borderRadius: 10, fontSize: 11, fontWeight: 600,
  background: 'rgba(107,114,128,0.15)', color: '#6b7280',
};

const PLATFORM_NAMES: Record<string, string> = {
  hackerone: 'HackerOne', bugcrowd: 'Bugcrowd', intigriti: 'Intigriti',
  yeswehack: 'YesWeHack', synack: 'Synack',
};

const MODE_OPTIONS = ['manual', 'prepare', 'automatic'];

export default function IdentityCenter() {
  const { t } = useI18n();

  const [data, setData] = useState<IdentityCenterData | null>(null);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState('');

  // Form states
  const [tokenInputs, setTokenInputs] = useState<Record<string, string>>({});
  const [emailInputs, setEmailInputs] = useState({ primary: '', secondary: '' });
  const [walletInputs, setWalletInputs] = useState<Record<string, string>>({});
  const [neverSubmit, setNeverSubmitState] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const d = await getIdentityCenter();
      setData(d);
      setEmailInputs({ primary: d.email?.primary || '', secondary: d.email?.secondary || '' });
      setWalletInputs(d.wallets || {});
      setNeverSubmitState(d.never_submit_without_approval ?? true);
    } catch {
      setMsg(t.identity_error);
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => { load(); }, [load]);

  const handleConnect = useCallback(async (provider: string) => {
    const token = tokenInputs[provider] || '';
    if (!token) { setMsg(`Token required for ${provider}`); return; }
    try {
      await connectPlatform(provider, token, '');
      setMsg(`${PLATFORM_NAMES[provider] || provider} connected`);
      setTokenInputs(p => ({ ...p, [provider]: '' }));
      load();
    } catch { setMsg(t.identity_error); }
  }, [tokenInputs, load, t]);

  const handleDisconnect = useCallback(async (provider: string) => {
    try {
      await disconnectPlatform(provider);
      load();
    } catch { setMsg(t.identity_error); }
  }, [load, t]);

  const handleRemove = useCallback(async (provider: string) => {
    try {
      await removePlatform(provider);
      load();
    } catch { setMsg(t.identity_error); }
  }, [load, t]);

  const handleModeChange = useCallback(async (provider: string, mode: string) => {
    try {
      await setPlatformMode(provider, mode);
      load();
    } catch { setMsg(t.identity_error); }
  }, [load, t]);

  const handleSaveEmail = useCallback(async () => {
    try {
      await setEmail(emailInputs.primary, emailInputs.secondary);
      setMsg(t.identity_saved);
    } catch { setMsg(t.identity_error); }
  }, [emailInputs, t]);

  const handleSaveWallets = useCallback(async () => {
    try {
      await setWallets(walletInputs);
      setMsg(t.identity_saved);
    } catch { setMsg(t.identity_error); }
  }, [walletInputs, t]);

  const handleToggleNeverSubmit = useCallback(async () => {
    const next = !neverSubmit;
    try {
      await setNeverSubmit(next);
      setNeverSubmitState(next);
      setMsg(t.identity_saved);
    } catch { setMsg(t.identity_error); }
  }, [neverSubmit, t]);

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh', color: '#7c8299' }}>
        {t.loading}...
      </div>
    );
  }

  return (
    <div style={{ padding: 24, maxWidth: 900, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: '#e0e0e0', margin: 0 }}>{t.identity_title}</h1>
        <p style={{ fontSize: 13, color: '#7c8299', margin: '4px 0 0' }}>{t.identity_vault}</p>
      </div>

      {/* Message toast */}
      {msg && (
        <div style={{
          padding: '10px 16px', borderRadius: 6, marginBottom: 20,
          background: msg.includes('Error') || msg.includes('error') ? 'rgba(239,68,68,0.1)' : 'rgba(34,197,94,0.1)',
          color: msg.includes('Error') || msg.includes('error') ? '#ef4444' : '#22c55e',
          fontSize: 13, fontWeight: 500,
        }}>
          {msg}
        </div>
      )}

      {/* Safety toggle */}
      <div style={{ ...cardStyle, marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: 14, fontWeight: 600, color: '#e0e0e0' }}>{t.identity_never_submit}</div>
            <div style={{ fontSize: 11, color: '#7c8299', marginTop: 2 }}>Bloquea envíos automáticos de reportes</div>
          </div>
          <button
            onClick={handleToggleNeverSubmit}
            style={{
              width: 44, height: 24, borderRadius: 12, border: 'none',
              background: neverSubmit ? '#7c3aed' : '#2a2e3d',
              cursor: 'pointer', position: 'relative', transition: 'background 0.15s',
              padding: 0,
            }}
          >
            <div style={{
              width: 18, height: 18, borderRadius: '50%',
              background: '#fff', position: 'absolute', top: 3,
              left: neverSubmit ? 24 : 3, transition: 'left 0.15s',
            }} />
          </button>
        </div>
      </div>

      {/* Platforms */}
      <div style={{ ...cardStyle, marginBottom: 20 }}>
        <div style={labelStyle}>{t.identity_platforms}</div>
        {(data?.platforms || []).length === 0 ? (
          <div style={{ color: '#7c8299', fontSize: 13, padding: '16px 0' }}>{t.identity_no_accounts}</div>
        ) : (
          (data?.platforms || []).map(p => {
            const isConnected = p.connected;
            return (
              <div key={p.provider} style={rowStyle}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, flex: 1 }}>
                  <div style={{ fontSize: 14, fontWeight: 600, color: '#e0e0e0', minWidth: 100 }}>
                    {PLATFORM_NAMES[p.provider] || p.provider}
                  </div>
                  <span style={isConnected ? badgeConnected : badgeDisconnected}>
                    {isConnected ? t.identity_connected : t.identity_disconnected}
                  </span>
                  {p.has_token && !isConnected && (
                    <span style={{ ...badgeConnected, background: 'rgba(234,179,8,0.15)', color: '#eab308' }}>
                      {t.identity_token_valid}
                    </span>
                  )}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
                  {/* Mode selector */}
                  <select
                    value={p.mode}
                    onChange={e => handleModeChange(p.provider, e.target.value)}
                    style={{
                      padding: '4px 8px', borderRadius: 4, border: '1px solid #2a2e3d',
                      background: '#11131f', color: '#e0e0e0', fontSize: 11, outline: 'none',
                    }}
                  >
                    {MODE_OPTIONS.map(m => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </select>

                  {/* Token input */}
                  {!isConnected && (
                    <input
                      placeholder="API Token"
                      value={tokenInputs[p.provider] || ''}
                      onChange={e => setTokenInputs(prev => ({ ...prev, [p.provider]: e.target.value }))}
                      style={{
                        width: 120, padding: '6px 8px', borderRadius: 4,
                        border: '1px solid #2a2e3d', background: '#11131f',
                        color: '#e0e0e0', fontSize: 11, outline: 'none',
                      }}
                    />
                  )}

                  {isConnected ? (
                    <button onClick={() => handleDisconnect(p.provider)} style={{ ...btnStyle, background: '#6b7280' }}>
                      {t.identity_disconnect}
                    </button>
                  ) : (
                    <button onClick={() => handleConnect(p.provider)} style={btnStyle}>
                      {t.identity_connect}
                    </button>
                  )}
                  {!isConnected && (
                    <button onClick={() => handleRemove(p.provider)} style={{ ...btnStyle, background: '#ef4444' }}>
                      {t.identity_remove}
                    </button>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Email */}
      <div style={{ ...cardStyle, marginBottom: 20 }}>
        <div style={labelStyle}>{t.identity_email}</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <div>
            <div style={{ fontSize: 12, color: '#7c8299', marginBottom: 4 }}>{t.identity_primary_email}</div>
            <input
              value={emailInputs.primary}
              onChange={e => setEmailInputs(p => ({ ...p, primary: e.target.value }))}
              style={inputStyle}
              placeholder="bugbounty@ejemplo.com"
            />
          </div>
          <div>
            <div style={{ fontSize: 12, color: '#7c8299', marginBottom: 4 }}>{t.identity_secondary_email}</div>
            <input
              value={emailInputs.secondary}
              onChange={e => setEmailInputs(p => ({ ...p, secondary: e.target.value }))}
              style={inputStyle}
              placeholder="rastro@ejemplo.com"
            />
          </div>
        </div>
        <button onClick={handleSaveEmail} style={{ ...btnStyle, marginTop: 16 }}>{t.identity_save}</button>
      </div>

      {/* Wallets */}
      <div style={{ ...cardStyle, marginBottom: 20 }}>
        <div style={labelStyle}>{t.identity_wallets}</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          {['usdc', 'binance', 'takenos', 'public'].map(key => (
            <div key={key}>
              <div style={{ fontSize: 12, color: '#7c8299', marginBottom: 4 }}>
                {key === 'usdc' ? t.identity_usdc : key === 'binance' ? t.identity_binance : key === 'takenos' ? t.identity_takenos : t.identity_public_wallet}
              </div>
              <input
                value={walletInputs[key] || ''}
                onChange={e => setWalletInputs(p => ({ ...p, [key]: e.target.value }))}
                style={inputStyle}
                placeholder={key === 'public' ? '0x...' : `${key} address`}
              />
            </div>
          ))}
        </div>
        <button onClick={handleSaveWallets} style={{ ...btnStyle, marginTop: 16 }}>{t.identity_save}</button>
      </div>

      {/* Footer */}
      <div style={{ textAlign: 'center', fontSize: 11, color: '#4a4f63' }}>
        {t.identity_vault} &mdash; Rastro v1.5.0
      </div>
    </div>
  );
}
