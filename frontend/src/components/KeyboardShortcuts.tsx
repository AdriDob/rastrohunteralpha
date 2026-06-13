import { useEffect, useState } from 'react';
import type { KeyboardShortcut } from '../types';

const SHORTCUTS: KeyboardShortcut[] = [
  { key: '⌘K / Ctrl+K', description: 'Open Command Palette', category: 'Global' },
  { key: '⌘B / Ctrl+B', description: 'Toggle Sidebar', category: 'Global' },
  { key: 'Escape', description: 'Close dialogs / palettes', category: 'Global' },
  { key: '↑↓', description: 'Navigate search results', category: 'Navigation' },
  { key: 'Enter', description: 'Select search result', category: 'Navigation' },
  { key: '⌘1-9', description: 'Navigate to page by index', category: 'Navigation' },
];

export default function KeyboardShortcutsDialog() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === '/') {
        e.preventDefault();
        setOpen(o => !o);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  if (!open) return null;

  return (
    <div
      style={{
        position: 'fixed', inset: 0, zIndex: 9998,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: 'rgba(0,0,0,0.6)',
      }}
      onClick={(e) => { if (e.target === e.currentTarget) setOpen(false); }}
    >
      <div
        style={{
          width: 480, background: '#1a1d29',
          border: '1px solid #2a2e3d', borderRadius: 12,
          boxShadow: '0 16px 48px rgba(0,0,0,0.6)',
          padding: 20,
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#fff' }}>Keyboard Shortcuts</h2>
          <span
            onClick={() => setOpen(false)}
            style={{ color: '#7c8299', fontSize: 12, cursor: 'pointer', padding: '4px 8px', borderRadius: 4, background: '#252836' }}
          >
            ESC
          </span>
        </div>

        {['Global', 'Navigation'].map(cat => {
          const sc = SHORTCUTS.filter(s => s.category === cat);
          return (
            <div key={cat} style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: '#7c8299', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 6 }}>{cat}</div>
              {sc.map((s, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: i < sc.length - 1 ? '1px solid #2a2e3d' : 'none' }}>
                  <span style={{ color: '#c4c7d0', fontSize: 13 }}>{s.description}</span>
                  <kbd style={{
                    padding: '2px 6px', borderRadius: 4, background: '#252836',
                    color: '#a78bfa', fontSize: 11, fontFamily: 'monospace',
                  }}>
                    {s.key}
                  </kbd>
                </div>
              ))}
            </div>
          );
        })}

        <div style={{ marginTop: 12, fontSize: 11, color: '#4a4f63', textAlign: 'center' }}>
          Press ⌘/ (Ctrl+/) to open this dialog anytime
        </div>
      </div>
    </div>
  );
}
