import { createContext, useContext, useEffect } from 'react';

export interface ThemeColors {
  background: string;
  surface: string;
  surfaceAlt: string;
  border: string;
  text: string;
  textSecondary: string;
  textMuted: string;
  accent: string;
  accentHover: string;
  success: string;
  warning: string;
  error: string;
  info: string;
}

export interface AppTheme {
  name: string;
  label: string;
  colors: ThemeColors;
}

export const detective_dark: AppTheme = {
  name: 'detective_dark',
  label: 'Detective Dark',
  colors: {
    background: '#0f111a',
    surface: '#1a1d29',
    surfaceAlt: '#1e2230',
    border: '#2a2e3d',
    text: '#e0e0e0',
    textSecondary: '#c4c7d0',
    textMuted: '#7c8299',
    accent: '#7c3aed',
    accentHover: '#6d28d9',
    success: '#22c55e',
    warning: '#f59e0b',
    error: '#ef4444',
    info: '#3b82f6',
  },
};

export const aurora_light: AppTheme = {
  name: 'aurora_light',
  label: 'Aurora Light',
  colors: {
    background: '#f8f9fc',
    surface: '#ffffff',
    surfaceAlt: '#f0f2f8',
    border: '#e2e4ed',
    text: '#1a1d29',
    textSecondary: '#4a4f63',
    textMuted: '#9ca3af',
    accent: '#7c3aed',
    accentHover: '#6d28d9',
    success: '#16a34a',
    warning: '#d97706',
    error: '#dc2626',
    info: '#2563eb',
  },
};

const themes: Record<string, AppTheme> = {
  detective_dark,
  aurora_light,
};

export function getTheme(name: string): AppTheme {
  return themes[name] || detective_dark;
}

export function applyTheme(theme: AppTheme): void {
  const root = document.documentElement;
  const c = theme.colors;
  root.style.setProperty('--bg-primary', c.background);
  root.style.setProperty('--bg-secondary', c.surface);
  root.style.setProperty('--bg-card', c.surfaceAlt);
  root.style.setProperty('--bg-hover', c.surfaceAlt);
  root.style.setProperty('--bg-pressed', c.surfaceAlt);
  root.style.setProperty('--border', c.border);
  root.style.setProperty('--border-hover', c.border);
  root.style.setProperty('--text-primary', c.text);
  root.style.setProperty('--text-secondary', c.textSecondary);
  root.style.setProperty('--text-muted', c.textMuted);
  root.style.setProperty('--text-faint', c.textMuted);
  root.style.setProperty('--accent', c.accent);
  root.style.setProperty('--accent-hover', c.accentHover);
  root.style.setProperty('--accent-glow', `${c.accent}1F`);
  root.style.setProperty('--success', c.success);
  root.style.setProperty('--warning', c.warning);
  root.style.setProperty('--error', c.error);
  root.style.setProperty('--info', c.info);
}

export interface ThemeContextValue {
  theme: AppTheme;
  setTheme: (name: string) => void;
  available: AppTheme[];
}

export const ThemeContext = createContext<ThemeContextValue>({
  theme: detective_dark,
  setTheme: () => {},
  available: [detective_dark, aurora_light],
});

export function useTheme(): ThemeContextValue {
  return useContext(ThemeContext);
}

export function useApplyTheme(theme: AppTheme): void {
  useEffect(() => {
    applyTheme(theme);
  }, [theme]);
}
