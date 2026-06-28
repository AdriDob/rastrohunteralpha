export const tokens = {
  colors: {
    base: '#05070A',
    surface: '#0B0F16',
    elevated: '#111827',
    card: '#161B22',
    hover: '#1C2333',
    border: '#212838',
    borderHover: '#2D3548',

    text: '#E2E4E9',
    textSecondary: '#C4C7D0',
    textMuted: '#7C8299',
    textFaint: '#4A4F63',

    primary: '#3B82F6',
    primaryHover: '#2563EB',
    primaryGlow: 'rgba(59,130,246,0.12)',

    accent: '#F59E0B',
    accentHover: '#D97706',
    accentGlow: 'rgba(245,158,11,0.12)',

    success: '#22C55E',
    warning: '#F59E0B',
    error: '#EF4444',
    info: '#3B82F6',

    glass: 'rgba(11,15,22,0.72)',
    glassBorder: 'rgba(33,40,56,0.6)',
    glassHighlight: 'rgba(255,255,255,0.03)',
  },

  spacing: {
    xs: '2px',
    sm: '4px',
    md: '8px',
    lg: '12px',
    xl: '16px',
    '2xl': '20px',
    '3xl': '24px',
    '4xl': '32px',
    '5xl': '40px',
  },

  radius: {
    sm: '4px',
    md: '6px',
    lg: '8px',
    xl: '12px',
    '2xl': '16px',
  },

  typography: {
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    mono: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
    sizes: {
      xs: '10px',
      sm: '11px',
      base: '13px',
      md: '14px',
      lg: '16px',
      xl: '20px',
      '2xl': '24px',
      '3xl': '30px',
    },
    weights: {
      regular: 400,
      medium: 500,
      semibold: 600,
      bold: 700,
    },
  },

  animation: {
    fast: '0.12s ease',
    normal: '0.15s ease',
    slow: '0.2s ease',
    spring: 'cubic-bezier(0.34, 1.56, 0.64, 1)',
  },

  shadow: {
    card: '0 1px 3px rgba(0,0,0,0.3)',
    elevated: '0 4px 12px rgba(0,0,0,0.4)',
    modal: '0 8px 32px rgba(0,0,0,0.5)',
    glow: (color: string) => `0 0 16px ${color}`,
  },
} as const;

export type RastroTokens = typeof tokens;
