import { useI18n } from '../lib/i18n';
import { useTheme } from '../lib/theme';

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

export default function Settings() {
  const { t, lang, setLang } = useI18n();
  const { theme, setTheme, available } = useTheme();

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
        <div style={labelStyle}>{t.about}</div>
        <div style={{ fontSize: 13, color: '#7c8299', lineHeight: 1.6 }}>
          <strong style={{ color: '#e0e0e0' }}>Rastro</strong> — v1.2.0
          <br />
          Sistema Operativo Privado de Investigación
          <br />
          <span style={{ fontSize: 11 }}>Build with 🕵️ for serious researchers</span>
        </div>
      </div>
    </div>
  );
}
