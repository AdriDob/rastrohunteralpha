import { useCallback, useEffect, useState } from 'react';
import { useI18n } from '../lib/i18n';
import { useTheme } from '../lib/theme';
import { getAIProviders, getAIConfig, updateAIConfig, type AIProviderInfo, type AIConfig } from '../lib/api';

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
  cursor: 'pointer', marginTop: 12,
};

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

  return (
    <div style={{ maxWidth: 640, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 20 }}>
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
      </div>

      <div style={cardStyle}>
        <div style={labelStyle}>{t.settings_section_language}</div>

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
