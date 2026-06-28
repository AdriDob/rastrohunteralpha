import { useCallback, useEffect, useState } from 'react';
import { useI18n } from '../lib/i18n';
import { useTheme } from '../lib/theme';
import { getAIProviders, getAIConfig, updateAIConfig, type AIProviderInfo, type AIConfig } from '../lib/api';
import { getMode, setMode, getPlatformConfigs, updatePlatformConfig, type PlatformConfig } from '../lib/api';

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

const rowColStyle: React.CSSProperties = {
  display: 'flex', flexDirection: 'column',
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
  cursor: 'pointer', marginTop: 12,
};

const PLATFORM_IDS = ['hackerone', 'bugcrowd', 'intigriti', 'yeswehack', 'synack'];

export default function Settings() {
  const { t, lang, setLang } = useI18n();
  const { theme, setTheme, available } = useTheme();

  // ── AI Settings state ──
  const [providers, setProviders] = useState<AIProviderInfo[]>([]);
  const [config, setConfig] = useState<AIConfig | null>(null);
  const [selProvider, setSelProvider] = useState('ollama');
  const [selHost, setSelHost] = useState('');
  const [selModel, setSelModel] = useState('');
  const [selApiKey, setSelApiKey] = useState('');
  const [selApiBase, setSelApiBase] = useState('');
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState('');

  useEffect(() => {
    getAIProviders().then(r => setProviders(r.providers)).catch(() => {});
    getAIConfig().then(c => {
      setConfig(c);
      setSelProvider(c.provider_type);
      setSelHost(c.host);
      setSelModel(c.model);
      setSelApiBase(c.api_base);
    }).catch(() => {});
  }, []);

  const selectedSpec = providers.find(p => p.id === selProvider);

  const handleSave = useCallback(async () => {
    setSaving(true);
    setMsg('');
    try {
      const body: any = { provider_type: selProvider };
      if (selProvider === 'ollama') {
        body.host = selHost;
        body.model = selModel;
      } else if (selProvider === 'openai') {
        body.api_base = selApiBase;
        body.model = selModel;
        if (selApiKey) body.api_key = selApiKey;
      }
      await updateAIConfig(body);
      setMsg(t.settings_ai_saved);
      const c = await getAIConfig();
      setConfig(c);
    } catch {
      setMsg(t.settings_ai_error);
    } finally {
      setSaving(false);
    }
  }, [selProvider, selHost, selModel, selApiKey, selApiBase, t]);

  // ── Mode state ──
  const [rastroMode, setRastroMode] = useState<'manual' | 'automatic'>('manual');
  const [modeMsg, setModeMsg] = useState('');

  useEffect(() => {
    getMode().then(r => setRastroMode(r.mode as 'manual' | 'automatic')).catch(() => {});
  }, []);

  const handleModeChange = useCallback(async (mode: 'manual' | 'automatic') => {
    try {
      await setMode(mode);
      setRastroMode(mode);
      setModeMsg(mode === 'manual' ? t.mode_manual : t.mode_automatic);
      setTimeout(() => setModeMsg(''), 2000);
    } catch {
      setModeMsg(t.settings_ai_error);
    }
  }, [t]);

  // ── Platform state ──
  const [platforms, setPlatforms] = useState<Record<string, PlatformConfig>>({});
  const [platformMsg, setPlatformMsg] = useState('');
  const [editingPlatform, setEditingPlatform] = useState<string | null>(null);

  useEffect(() => {
    getPlatformConfigs().then(r => {
      const p: Record<string, PlatformConfig> = {};
      for (const key of PLATFORM_IDS) {
        p[key] = r[key] || { enabled: false, action: 'prepare_only', username: '', api_key: '' };
      }
      setPlatforms(p);
    }).catch(() => {});
  }, []);

  const handlePlatformSave = useCallback(async (pid: string) => {
    try {
      await updatePlatformConfig(pid, platforms[pid]);
      setPlatformMsg(t.platform_saved);
      setTimeout(() => setPlatformMsg(''), 2000);
      setEditingPlatform(null);
    } catch {
      setPlatformMsg(t.platform_save_error);
    }
  }, [platforms, t]);

  const platformLabels: Record<string, string> = {
    hackerone: 'HackerOne',
    bugcrowd: 'Bugcrowd',
    intigriti: 'Intigriti',
    yeswehack: 'YesWeHack',
    synack: 'Synack',
  };

  return (
    <div style={{ maxWidth: 720, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: '#e0e0e0', margin: 0 }}>{t.settings_title}</h1>
        <p style={{ fontSize: 13, color: '#7c8299', margin: '4px 0 0' }}>{t.settings}</p>
      </div>

      <div style={cardStyle}>
        <div style={labelStyle}>{t.settings_section_appearance}</div>

        <div style={rowStyle}>
          <div>
            <div style={{ fontSize: 14, fontWeight: 600, color: '#e0e0e0' }}>{t.theme}</div>
            <div style={{ fontSize: 12, color: '#7c8299', marginTop: 2 }}>{t.settings_theme_desc}</div>
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            {available.map((t) => (
              <button
                key={t.name}
                onClick={() => setTheme(t.name)}
                style={{
                  padding: '6px 14px', borderRadius: 6, border: '1px solid #2a2e3d',
                  background: theme.name === t.name ? '#7c3aed' : 'transparent',
                  color: theme.name === t.name ? '#fff' : '#7c8299',
                  fontSize: 12, fontWeight: 600, cursor: 'pointer',
                  transition: 'all 0.12s',
                }}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        <div style={rowStyle}>
          <div>
            <div style={{ fontSize: 14, fontWeight: 600, color: '#e0e0e0' }}>{t.language}</div>
            <div style={{ fontSize: 12, color: '#7c8299', marginTop: 2 }}>{t.settings_language_desc}</div>
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            {(['en', 'es'] as const).map((l) => (
              <button
                key={l}
                onClick={() => setLang(l)}
                style={{
                  padding: '6px 14px', borderRadius: 6, border: '1px solid #2a2e3d',
                  background: lang === l ? '#7c3aed' : 'transparent',
                  color: lang === l ? '#fff' : '#7c8299',
                  fontSize: 12, fontWeight: 600, cursor: 'pointer',
                  transition: 'all 0.12s',
                }}
              >
                {l === 'en' ? 'English' : 'Español'}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Mode card */}
      <div style={cardStyle}>
        <div style={labelStyle}>{t.mode_title}</div>
        <div style={{ fontSize: 13, color: '#7c8299', marginBottom: 16 }}>{t.mode_description}</div>

        <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
          {(['manual', 'automatic'] as const).map((m) => (
            <button
              key={m}
              onClick={() => handleModeChange(m)}
              style={{
                flex: 1, padding: '16px', borderRadius: 8,
                border: rastroMode === m ? '2px solid #7c3aed' : '1px solid #2a2e3d',
                background: rastroMode === m ? '#1a1d29' : '#11131f',
                color: '#e0e0e0', cursor: 'pointer',
                textAlign: 'left', transition: 'all 0.12s',
              }}
            >
              <div style={{ fontSize: 15, fontWeight: 700, color: rastroMode === m ? '#a78bfa' : '#e0e0e0' }}>
                {m === 'manual' ? t.mode_manual : t.mode_automatic}
              </div>
              <div style={{ fontSize: 12, color: '#7c8299', marginTop: 6 }}>
                {m === 'manual' ? t.mode_manual_desc : t.mode_automatic_desc}
              </div>
            </button>
          ))}
        </div>

        {rastroMode === 'automatic' && (
          <div style={{ fontSize: 12, color: '#f59e0b', padding: '8px 12px', background: '#1a1d29', borderRadius: 6 }}>
            {t.mode_caution}
          </div>
        )}

        {modeMsg && (
          <div style={{ fontSize: 12, color: '#22c55e', marginTop: 8 }}>{modeMsg}</div>
        )}
      </div>

      {/* Platform integration card */}
      <div style={cardStyle}>
        <div style={labelStyle}>{t.platform_title}</div>
        <div style={{ fontSize: 13, color: '#7c8299', marginBottom: 16 }}>{t.platform_description}</div>

        {PLATFORM_IDS.map(pid => (
          <div key={pid} style={{ ...rowColStyle, gap: 8 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ fontSize: 14, fontWeight: 600, color: '#e0e0e0' }}>
                {platformLabels[pid] || pid}
              </div>
              <button
                onClick={() => setEditingPlatform(editingPlatform === pid ? null : pid)}
                style={{
                  padding: '4px 12px', borderRadius: 4, border: '1px solid #2a2e3d',
                  background: 'transparent', color: '#7c8299', fontSize: 11, cursor: 'pointer',
                }}
              >
                {editingPlatform === pid ? '▲' : '▼'}
              </button>
            </div>

            {editingPlatform === pid && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10, padding: '8px 0' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: '#e0e0e0' }}>
                  <input
                    type="checkbox"
                    checked={platforms[pid]?.enabled || false}
                    onChange={e => setPlatforms(p => ({ ...p, [pid]: { ...p[pid], enabled: e.target.checked } }))}
                  />
                  {t.platform_enabled}
                </label>

                <div>
                  <div style={{ fontSize: 12, color: '#7c8299', marginBottom: 4 }}>{t.platform_action}</div>
                  <select
                    value={platforms[pid]?.action || 'prepare_only'}
                    onChange={e => setPlatforms(p => ({ ...p, [pid]: { ...p[pid], action: e.target.value as any } }))}
                    style={inputStyle}
                  >
                    <option value="prepare_only">{t.platform_action_prepare}</option>
                    <option value="prepare_and_open">{t.platform_action_open}</option>
                    <option value="prepare_and_fill">{t.platform_action_fill}</option>
                    <option value="auto_submit">{t.platform_action_auto}</option>
                  </select>
                </div>

                <div>
                  <div style={{ fontSize: 12, color: '#7c8299', marginBottom: 4 }}>{t.platform_username}</div>
                  <input
                    style={inputStyle}
                    value={platforms[pid]?.username || ''}
                    onChange={e => setPlatforms(p => ({ ...p, [pid]: { ...p[pid], username: e.target.value } }))}
                    placeholder="username@example.com"
                  />
                </div>

                <div>
                  <div style={{ fontSize: 12, color: '#7c8299', marginBottom: 4 }}>{t.platform_api_key}</div>
                  <input
                    style={inputStyle}
                    type="password"
                    value={platforms[pid]?.api_key || ''}
                    onChange={e => setPlatforms(p => ({ ...p, [pid]: { ...p[pid], api_key: e.target.value } }))}
                    placeholder="..."
                  />
                </div>

                <button onClick={() => handlePlatformSave(pid)} style={btnStyle}>
                  {t.settings_ai_save}
                </button>
              </div>
            )}
          </div>
        ))}

        {platformMsg && (
          <div style={{ fontSize: 12, color: '#22c55e', marginTop: 8 }}>{platformMsg}</div>
        )}
      </div>

      {/* AI Settings */}
      <div style={cardStyle}>
        <div style={labelStyle}>{t.settings_section_ai}</div>

        <div style={rowStyle}>
          <div>
            <div style={{ fontSize: 14, fontWeight: 600, color: '#e0e0e0' }}>{t.settings_ai_provider}</div>
            <div style={{ fontSize: 12, color: '#7c8299', marginTop: 2 }}>{t.settings_ai_provider_desc}</div>
          </div>
          {config && (
            <span style={{ fontSize: 11, color: config.available ? '#22c55e' : '#ef4444' }}>
              {config.available ? t.settings_ai_available : t.settings_ai_unavailable}
            </span>
          )}
        </div>

        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 12 }}>
          {providers.map(p => (
            <button
              key={p.id}
              onClick={() => { setSelProvider(p.id); setSelModel(p.models[0] || ''); }}
              style={{
                padding: '6px 14px', borderRadius: 6, border: '1px solid #2a2e3d',
                background: selProvider === p.id ? '#7c3aed' : 'transparent',
                color: selProvider === p.id ? '#fff' : '#7c8299',
                fontSize: 12, fontWeight: 600, cursor: 'pointer',
                opacity: p.available === false ? 0.5 : 1,
                transition: 'all 0.12s',
              }}
            >
              {p.label}
              {p.active && ` (${t.settings_ai_active})`}
            </button>
          ))}
        </div>

        {selProvider === 'ollama' && (
          <>
            <div>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#e0e0e0' }}>{t.settings_ai_host}</div>
              <div style={{ fontSize: 11, color: '#7c8299', marginTop: 2 }}>{t.settings_ai_host_desc}</div>
              <input style={inputStyle} value={selHost} onChange={e => setSelHost(e.target.value)} placeholder="http://localhost:11434" />
            </div>
            <div style={{ marginTop: 12 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#e0e0e0' }}>{t.settings_ai_model}</div>
              <div style={{ fontSize: 11, color: '#7c8299', marginTop: 2 }}>{t.settings_ai_model_desc}</div>
              <select
                value={selModel}
                onChange={e => setSelModel(e.target.value)}
                style={{ ...inputStyle, cursor: 'pointer' }}
              >
                {(selectedSpec?.models || []).map(m => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </div>
          </>
        )}

        {selProvider === 'openai' && (
          <>
            <div>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#e0e0e0' }}>{t.settings_ai_host}</div>
              <div style={{ fontSize: 11, color: '#7c8299', marginTop: 2 }}>{t.settings_ai_host_desc}</div>
              <input style={inputStyle} value={selApiBase} onChange={e => setSelApiBase(e.target.value)} placeholder="https://api.openai.com/v1" />
            </div>
            <div style={{ marginTop: 12 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#e0e0e0' }}>{t.settings_ai_model}</div>
              <div style={{ fontSize: 11, color: '#7c8299', marginTop: 2 }}>{t.settings_ai_model_desc}</div>
              <select
                value={selModel}
                onChange={e => setSelModel(e.target.value)}
                style={{ ...inputStyle, cursor: 'pointer' }}
              >
                {(selectedSpec?.models || []).map(m => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </div>
            <div style={{ marginTop: 12 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#e0e0e0' }}>{t.settings_ai_api_key}</div>
              <div style={{ fontSize: 11, color: '#7c8299', marginTop: 2 }}>{t.settings_ai_api_key_desc}</div>
              <input style={inputStyle} type="password" value={selApiKey} onChange={e => setSelApiKey(e.target.value)} placeholder="sk-..." />
            </div>
          </>
        )}

        {selProvider === 'local' && (
          <div style={{ fontSize: 13, color: '#7c8299', padding: '12px 0' }}>
            {t.settings_ai_available} — {t.settings_ai_save} {t.settings_ai_active}
          </div>
        )}

        <button onClick={handleSave} disabled={saving} style={{ ...btnStyle, opacity: saving ? 0.6 : 1 }}>
          {saving ? '...' : t.settings_ai_save}
        </button>
        {msg && (
          <div style={{ fontSize: 12, color: msg.includes('Error') || msg.includes('error') ? '#ef4444' : '#22c55e', marginTop: 8 }}>
            {msg}
          </div>
        )}
      </div>

      <div style={cardStyle}>
        <div style={labelStyle}>{t.about}</div>
        <div style={{ fontSize: 13, color: '#7c8299', lineHeight: 1.6 }}>
          <strong style={{ color: '#e0e0e0' }}>Rastro</strong> — v1.4.0-rc1
          <br />
          Sistema Operativo Privado de Investigación
          <br />
          <span style={{ fontSize: 11 }}>Build with 🕵️ for serious researchers</span>
        </div>
      </div>
    </div>
  );
}
