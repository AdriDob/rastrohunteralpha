import { useEffect, useRef, useState, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useStore } from '../lib/store';
import { getTargets, getOpportunityTop, getAssistantRecommendations } from '../lib/api';
import type { Target, OpportunityItem, AssistantRecommendation } from '../types';

type CmdCategory = 'Navigation' | 'Actions' | 'Settings' | 'Targets' | 'Opportunities' | 'AI Suggestions' | 'Recent';

interface CmdItem {
  id: string;
  label: string;
  description: string;
  action: () => void;
  category: CmdCategory;
  icon: string;
  shortcut?: string;
}

type Mode = 'all' | 'nav' | 'act' | 'target';

const ROUTE_MAP: Record<string, string> = {
  'go-dashboard': '/',
  'go-daily': '/daily',
  'go-radar': '/radar',
  'go-intel': '/intelligence',
  'go-evidence': '/evidence',
  'go-reports': '/reports',
  'go-replay': '/replay',
  'go-screenshots': '/screenshots',
  'go-pipeline': '/pipeline',
  'go-confidence': '/confidence',
  'go-hypotheses': '/hypothesis',
  'go-operations': '/operations',
  'go-tasks': '/tasks',
  'go-hotpaths': '/hotpaths',
  'go-surface': '/surface',
  'go-differential': '/differential',
  'go-insights': '/insights',
  'go-actions': '/actions',
  'go-history': '/history',
  'go-intelligence': '/intelligence',
};

const NAV_ITEMS: CmdItem[] = [
  // Mission
  { id: 'go-dashboard', label: 'Mission Control', description: 'Investigation hub', action: () => null, category: 'Navigation', icon: '◈', shortcut: 'g m' },
  { id: 'go-daily', label: 'Daily Briefing', description: 'Morning intelligence summary', action: () => null, category: 'Navigation', icon: '🌅', shortcut: 'g d' },
  // Recon
  { id: 'go-surface', label: 'Attack Surface', description: 'Target surface mapping', action: () => null, category: 'Navigation', icon: '◉', shortcut: 'g s' },
  { id: 'go-hotpaths', label: 'Hot Paths', description: 'Hot path analysis', action: () => null, category: 'Navigation', icon: '⚡', shortcut: 'g h' },
  // Findings
  { id: 'go-evidence', label: 'Evidence Center', description: 'Review evidence records', action: () => null, category: 'Navigation', icon: '📋', shortcut: 'g e' },
  { id: 'go-screenshots', label: 'Screenshots', description: 'Evidence screenshots', action: () => null, category: 'Navigation', icon: '🖼', shortcut: 'g sc' },
  { id: 'go-pipeline', label: 'Pipeline', description: 'Findings pipeline status', action: () => null, category: 'Navigation', icon: '▤', shortcut: 'g p' },
  // Analysis
  { id: 'go-insights', label: 'Insights', description: 'Cross-target insights', action: () => null, category: 'Navigation', icon: '◎', shortcut: 'g i' },
  { id: 'go-hypotheses', label: 'Hypothesis Queue', description: 'Attack hypotheses', action: () => null, category: 'Navigation', icon: '⟐', shortcut: 'g hy' },
  { id: 'go-differential', label: 'Differential Engine', description: 'Cross-target differential analysis', action: () => null, category: 'Navigation', icon: 'Δ', shortcut: 'g df' },
  { id: 'go-confidence', label: 'Confidence Dashboard', description: 'Confidence audits', action: () => null, category: 'Navigation', icon: '📊', shortcut: 'g c' },
  { id: 'go-replay', label: 'Replay Center', description: 'Investigation replays', action: () => null, category: 'Navigation', icon: '🔄', shortcut: 'g r' },
  // Operations
  { id: 'go-actions', label: 'Actions', description: 'Execution decisions', action: () => null, category: 'Navigation', icon: '▶', shortcut: 'g a' },
  { id: 'go-operations', label: 'Operations Dashboard', description: 'Operations center', action: () => null, category: 'Navigation', icon: '⚙', shortcut: 'g o' },
  { id: 'go-tasks', label: 'Task Queue', description: 'Manage investigation tasks', action: () => null, category: 'Navigation', icon: '✓', shortcut: 'g t' },
  { id: 'go-history', label: 'History', description: 'Audit trail', action: () => null, category: 'Navigation', icon: '☰', shortcut: 'g hi' },
  // Intelligence
  { id: 'go-intel', label: 'AI Intelligence', description: 'AI-driven insights', action: () => null, category: 'Navigation', icon: '🧠', shortcut: 'g ai' },
  { id: 'go-radar', label: 'Opportunity Radar', description: 'Find and evaluate targets', action: () => null, category: 'Navigation', icon: '◎', shortcut: 'g ra' },
  { id: 'go-reports', label: 'Report Center', description: 'Generate and view reports', action: () => null, category: 'Navigation', icon: '📄', shortcut: 'g re' },
  { id: 'go-intelligence', label: 'Opportunity Intelligence', description: 'Bug bounty opportunity discovery', action: () => null, category: 'Navigation', icon: '🎯', shortcut: 'g op' },
  // ── Actions ────────────────────────────────────────────────────
  { id: 'act-discovery', label: 'Run Discovery Engine', description: 'Scan and discover new endpoints', action: () => null, category: 'Actions', icon: '🔍' },
  { id: 'act-generate-report', label: 'Generate Report', description: 'Create a comprehensive report', action: () => null, category: 'Actions', icon: '📄' },
  { id: 'act-intel-refresh', label: 'Refresh Intelligence', description: 'Re-run intelligence analysis', action: () => null, category: 'Actions', icon: '🔄' },
  { id: 'act-top-opp', label: 'Open Top Opportunity', description: 'Navigate to the highest-value target', action: () => null, category: 'Actions', icon: '🏆' },
  { id: 'act-investigation', label: 'Explain Investigation State', description: 'Full investigation state analysis for current target', action: () => null, category: 'Actions', icon: '🔬' },
  { id: 'act-bounty', label: 'Estimate Bounty Potential', description: 'Analyze payout potential based on real signals', action: () => null, category: 'Actions', icon: '💰' },
];

const MODES: { key: Mode; label: string; icon: string }[] = [
  { key: 'all', label: 'All', icon: '◈' },
  { key: 'nav', label: 'Navigate', icon: '→' },
  { key: 'act', label: 'Actions', icon: '▶' },
  { key: 'target', label: 'Targets', icon: '🎯' },
];

export default function CommandPalette() {
  const { commandPaletteOpen, setCommandPaletteOpen, incrementCommandPaletteUsage, recentInvestigations } = useStore();
  const [query, setQuery] = useState('');
  const [items, setItems] = useState<CmdItem[]>([]);
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [mode, setMode] = useState<Mode>('all');
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  const go = useCallback((path: string) => {
    setCommandPaletteOpen(false);
    navigate(path);
  }, [navigate, setCommandPaletteOpen]);

  useEffect(() => {
    if (commandPaletteOpen) {
      incrementCommandPaletteUsage();
      setQuery('');
      setSelectedIdx(0);
      setMode('all');
      setTimeout(() => inputRef.current?.focus(), 50);

      const dynamicItems: CmdItem[] = NAV_ITEMS.map(item => {
        const route = ROUTE_MAP[item.id];
        if (route) {
          return { ...item, action: () => go(route) };
        }
        if (item.id === 'act-discovery') return { ...item, action: () => go('/pipeline') };
        if (item.id === 'act-generate-report') return { ...item, action: () => go('/reports') };
        if (item.id === 'act-intel-refresh') return { ...item, action: () => go('/intelligence') };
        if (item.id === 'act-top-opp') return { ...item, action: () => go('/radar') };
        if (item.id === 'act-investigation') return { ...item, action: () => go('/insights') };
        if (item.id === 'act-bounty') return { ...item, action: () => go('/intelligence') };
        return item;
      });

      dynamicItems.push(
        { id: 'toggle-dark', label: 'Toggle Dark Mode', description: 'Switch between dark and light theme', action: () => { window.location.reload(); }, category: 'Settings', icon: '🌙' },
        { id: 'toggle-lang', label: 'Toggle Language', description: 'Switch between English and Spanish', action: () => { window.location.reload(); }, category: 'Settings', icon: '🌐' },
        { id: 'toggle-ai', label: 'Toggle AI Copilot', description: 'Open or close the AI assistant panel', action: () => { useStore.getState().setAssistantOpen(!useStore.getState().assistantOpen); setCommandPaletteOpen(false); }, category: 'Settings', icon: '🧠' },
      );

      const recent = recentInvestigations.slice(0, 5);
      recent.forEach(r => {
        dynamicItems.push({
          id: `recent-${r.targetId}`,
          label: r.targetName,
          description: 'Recent investigation',
          action: () => go(`/target/${r.targetId}`),
          category: 'Recent',
          icon: '🕐',
        });
      });

      getTargets({ limit: 10 }).then(r => {
        r.items.forEach((t: Target) => {
          if (recent.some(r => r.targetId === t.id)) return;
          dynamicItems.push({
            id: `target-${t.id}`, label: `Target: ${t.name}`,
            description: `${t.endpoint_count} endpoints · $${(t.estimated_payout ?? 0).toLocaleString()} est. payout`,
            action: () => go(`/target/${t.id}`), category: 'Targets', icon: '🎯',
          });
        });
      }).catch(() => {});

      getOpportunityTop(10).then(r => {
        (r.opportunities ?? []).forEach((o: OpportunityItem) => {
          dynamicItems.push({
            id: `opp-${o.id}`, label: `Opportunity: ${o.name}`,
            description: `${o.category} · score ${(o.score ?? 0).toFixed(2)} · ${o.source_name}`,
            action: () => { if (o.public_url) window.open(o.public_url, '_blank'); setCommandPaletteOpen(false); },
            category: 'Opportunities', icon: '💎',
          });
        });
      }).catch(() => {});

      getAssistantRecommendations().then(r => {
        (r.recommendations ?? []).slice(0, 3).forEach((rec: AssistantRecommendation) => {
          dynamicItems.push({
            id: `rec-${rec.type}-${rec.action}`.replace(/\s+/g, '-'),
            label: `AI: ${rec.action}`,
            description: rec.reason,
            action: () => { if (rec.endpoint) go('/evidence'); },
            category: 'AI Suggestions', icon: '🤖',
          });
        });
      }).catch(() => {});

      setItems(dynamicItems);
    }
  }, [commandPaletteOpen, navigate, setCommandPaletteOpen, go, incrementCommandPaletteUsage, recentInvestigations]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setCommandPaletteOpen(!commandPaletteOpen);
      }
      if (e.key === 'Escape' && commandPaletteOpen) {
        setCommandPaletteOpen(false);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [commandPaletteOpen, setCommandPaletteOpen]);

  const filtered = useMemo(() => {
    const raw = query.trim()
      ? items.filter(i =>
          i.label.toLowerCase().includes(query.toLowerCase()) ||
          i.description.toLowerCase().includes(query.toLowerCase()) ||
          i.category.toLowerCase().includes(query.toLowerCase()),
        )
      : items;

    if (mode === 'all') return raw;
    if (mode === 'nav') return raw.filter(i => i.category === 'Navigation');
    if (mode === 'act') return raw.filter(i => i.category === 'Actions');
    if (mode === 'target') return raw.filter(i => i.category === 'Targets' || i.category === 'Opportunities' || i.category === 'Recent');
    return raw;
  }, [items, query, mode]);

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setSelectedIdx(i => Math.min(i + 1, filtered.length - 1)); }
    if (e.key === 'ArrowUp') { e.preventDefault(); setSelectedIdx(i => Math.max(i - 1, 0)); }
    if (e.key === 'Enter' && filtered[selectedIdx]) {
      setCommandPaletteOpen(false);
      filtered[selectedIdx].action();
    }
  };

  if (!commandPaletteOpen) return null;

  const categories = [...new Set(filtered.map(i => i.category))];

  return (
    <div
      style={{
        position: 'fixed', inset: 0, zIndex: 9999,
        display: 'flex', alignItems: 'flex-start', justifyContent: 'center',
        paddingTop: '10vh',
      }}
      onClick={(e) => { if (e.target === e.currentTarget) setCommandPaletteOpen(false); }}
    >
      <div
        style={{
          width: 620, maxHeight: '65vh', background: '#1a1d29',
          border: '1px solid #2a2e3d', borderRadius: 12,
          boxShadow: '0 16px 48px rgba(0,0,0,0.6)',
          display: 'flex', flexDirection: 'column', overflow: 'hidden',
        }}
      >
        <div style={{ padding: '12px 16px', borderBottom: '1px solid #2a2e3d', display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ color: '#7c8299', fontSize: 16 }}>⌘</span>
          <input
            ref={inputRef}
            value={query}
            onChange={e => { setQuery(e.target.value); setSelectedIdx(0); }}
            onKeyDown={handleKey}
            placeholder="Search pages, targets, opportunities, actions..."
            style={{
              flex: 1, background: 'transparent', border: 'none', outline: 'none',
              color: '#e0e0e0', fontSize: 14,
            }}
          />
          <span style={{ color: '#4a4f63', fontSize: 11, background: '#252836', padding: '2px 6px', borderRadius: 4 }}>ESC</span>
        </div>

        {/* Mode tabs */}
        <div style={{
          display: 'flex', gap: 2, padding: '6px 12px',
          borderBottom: '1px solid #2a2e3d',
        }}>
          {MODES.map(m => (
            <button
              key={m.key}
              onClick={() => { setMode(m.key); setSelectedIdx(0); }}
              style={{
                padding: '4px 10px', borderRadius: 6, border: 'none',
                background: mode === m.key ? '#7c3aed' : 'transparent',
                color: mode === m.key ? '#fff' : '#7c8299',
                fontSize: 11, fontWeight: 600, cursor: 'pointer',
                display: 'flex', alignItems: 'center', gap: 4,
                transition: 'all 0.12s',
              }}
              onMouseEnter={e => { if (mode !== m.key) e.currentTarget.style.background = '#252836'; }}
              onMouseLeave={e => { if (mode !== m.key) e.currentTarget.style.background = 'transparent'; }}
            >
              <span>{m.icon}</span>
              <span>{m.label}</span>
            </button>
          ))}
        </div>

        <div style={{ overflow: 'auto', flex: 1, padding: '4px 0' }}>
          {filtered.length === 0 && (
            <div style={{ padding: '24px 16px', textAlign: 'center', color: '#4a4f63', fontSize: 13 }}>
              No results for "{query}"
            </div>
          )}
          {categories.map(cat => {
            const catItems = filtered.filter(i => i.category === cat);
            if (!catItems.length) return null;
            return (
              <div key={cat}>
                <div style={{ padding: '6px 16px', fontSize: 10, fontWeight: 700, color: '#4a4f63', textTransform: 'uppercase', letterSpacing: 1, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span>{cat}</span>
                  <span style={{
                    fontSize: 9, color: '#6b7280', background: '#252836',
                    padding: '0 5px', borderRadius: 8, lineHeight: '16px',
                  }}>
                    {catItems.length}
                  </span>
                </div>
                {catItems.map((item) => {
                  const globalIdx = filtered.indexOf(item);
                  return (
                    <div
                      key={item.id}
                      onClick={() => { setCommandPaletteOpen(false); item.action(); }}
                      onMouseEnter={() => setSelectedIdx(globalIdx)}
                      style={{
                        padding: '8px 16px', cursor: 'pointer', display: 'flex', gap: 10, alignItems: 'center',
                        background: globalIdx === selectedIdx ? '#252836' : 'transparent',
                        transition: 'background 0.1s',
                      }}
                    >
                      <span style={{ fontSize: 14, minWidth: 24, textAlign: 'center' }}>{item.icon}</span>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 13, color: '#e0e0e0', fontWeight: globalIdx === selectedIdx ? 600 : 400 }}>{item.label}</div>
                        <div style={{ fontSize: 11, color: '#7c8299', marginTop: 1 }}>{item.description}</div>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        {item.shortcut && (
                          <span style={{
                            fontSize: 9, color: '#4a4f63', background: '#1e2130',
                            padding: '1px 5px', borderRadius: 4, fontFamily: 'monospace',
                          }}>
                            {item.shortcut}
                          </span>
                        )}
                        <span style={{ color: '#4a4f63', fontSize: 10 }}>{item.category}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}