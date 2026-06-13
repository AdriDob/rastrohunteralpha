import { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useStore } from '../../lib/store';
import { useTheme } from '../../lib/theme';
import { useI18n } from '../../lib/i18n';
import NotificationsDropdown from '../NotificationsDropdown';

interface NavItem {
  to: string;
  label: string;
  icon: string;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

const navSections: NavSection[] = [
  {
    title: 'Mission',
    items: [
      { to: '/', label: 'Mission Control', icon: '◈' },
      { to: '/daily', label: 'Daily Briefing', icon: '🌅' },
    ],
  },
  {
    title: 'Recon',
    items: [
      { to: '/surface', label: 'Attack Surface', icon: '◉' },
      { to: '/hotpaths', label: 'Hot Paths', icon: '⚡' },
      { to: '/target/:id', label: 'Target Detail', icon: '🎯' },
    ],
  },
  {
    title: 'Findings',
    items: [
      { to: '/evidence', label: 'Evidence Center', icon: '📋' },
      { to: '/screenshots', label: 'Screenshots', icon: '🖼️' },
      { to: '/pipeline', label: 'Pipeline', icon: '▤' },
    ],
  },
  {
    title: 'Analysis',
    items: [
      { to: '/insights', label: 'Insights', icon: '◎' },
      { to: '/hypothesis', label: 'Hypotheses', icon: '⟐' },
      { to: '/differential', label: 'Differential', icon: 'Δ' },
      { to: '/confidence', label: 'Confidence', icon: '📊' },
      { to: '/replay', label: 'Replay', icon: '🔄' },
    ],
  },
  {
    title: 'Operations',
    items: [
      { to: '/actions', label: 'Actions', icon: '▶' },
      { to: '/operations', label: 'Operations', icon: '⚙' },
      { to: '/tasks', label: 'Tasks', icon: '✓' },
      { to: '/history', label: 'History', icon: '☰' },
    ],
  },
  {
    title: 'Intelligence',
    items: [
      { to: '/intelligence', label: 'AI Intelligence', icon: '🧠' },
      { to: '/radar', label: 'Opportunity Radar', icon: '◎' },
      { to: '/reports', label: 'Reports', icon: '📄' },
    ],
  },
];

const collapsedWidth = 56;
const expandedWidth = 200;

const btnSmallStyle: React.CSSProperties = {
  background: 'transparent', border: 'none', color: '#7c8299', cursor: 'pointer',
  fontSize: 14, padding: '4px 6px', borderRadius: 4,
};

export function DesktopSidebar({ isExpanded }: { isExpanded: boolean }) {
  const { toggleSidebar, recentInvestigations, favoriteTargets, assistantOpen, setAssistantOpen } = useStore();
  const { theme, setTheme } = useTheme();
  const { lang, setLang } = useI18n();
  const navigate = useNavigate();
  const [collapsedSections, setCollapsedSections] = useState<Set<string>>(new Set());
  const [navFilter, setNavFilter] = useState('');

  const toggleSection = (title: string) => {
    setCollapsedSections(prev => {
      const next = new Set(prev);
      if (next.has(title)) next.delete(title);
      else next.add(title);
      return next;
    });
  };

  const filterMatches = (label: string) =>
    !navFilter.trim() || label.toLowerCase().includes(navFilter.toLowerCase());

  const favInvestigations = recentInvestigations.filter(r => favoriteTargets.includes(r.targetId));
  const recentOnly = recentInvestigations.filter(r => !favoriteTargets.includes(r.targetId));

  return (
    <aside
      style={{
        width: isExpanded ? expandedWidth : collapsedWidth,
        background: '#1a1d29', borderRight: '1px solid #2a2e3d',
        display: 'flex', flexDirection: 'column', flexShrink: 0,
        transition: 'width 0.15s ease', overflow: 'hidden',
      }}
    >
      {/* Logo + controls */}
      <div style={{
        padding: isExpanded ? '16px 20px' : '12px 0',
        borderBottom: '1px solid #2a2e3d', flexShrink: 0,
        display: 'flex', alignItems: 'center', justifyContent: isExpanded ? 'space-between' : 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 32, height: 32, borderRadius: 6,
            background: 'linear-gradient(135deg,#7c3aed,#a855f7)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#fff', fontWeight: 800, fontSize: 14, flexShrink: 0,
          }}>R</div>
          {isExpanded && <span style={{ fontWeight: 800, fontSize: 16, letterSpacing: 2, color: '#fff' }}>RASTRO</span>}
        </div>
        {isExpanded && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <button
              onClick={() => setTheme(theme.name === 'detective_dark' ? 'aurora_light' : 'detective_dark')}
              style={btnSmallStyle}
              onMouseEnter={e => { e.currentTarget.style.color = '#fff'; }}
              onMouseLeave={e => { e.currentTarget.style.color = '#7c8299'; }}
            >
              {theme.name === 'detective_dark' ? '☀' : '☾'}
            </button>
            <button
              onClick={() => setLang(lang === 'en' ? 'es' : 'en')}
              style={{ ...btnSmallStyle, fontSize: 11, fontWeight: 700, letterSpacing: 0.5 }}
              onMouseEnter={e => { e.currentTarget.style.color = '#fff'; }}
              onMouseLeave={e => { e.currentTarget.style.color = '#7c8299'; }}
            >
              {lang === 'en' ? 'EN' : 'ES'}
            </button>
            <NotificationsDropdown />
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav style={{
        flex: 1, padding: isExpanded ? '8px 8px' : '8px 4px',
        display: 'flex', flexDirection: 'column', gap: 4,
        overflowY: 'auto', overflowX: 'hidden',
      }}>
        {/* Search filter */}
        {isExpanded && (
          <div style={{ padding: '4px 4px 8px' }}>
            <input
              value={navFilter}
              onChange={e => setNavFilter(e.target.value)}
              placeholder="Filter pages..."
              style={{
                width: '100%', padding: '6px 8px', borderRadius: 6, border: '1px solid #2a2e3d',
                background: '#12141f', color: '#e0e0e0', fontSize: 11, outline: 'none',
                boxSizing: 'border-box',
              }}
            />
          </div>
        )}

        {navSections.map(section => {
          const filteredItems = section.items.filter(i => filterMatches(i.label));
          if (navFilter.trim() && filteredItems.length === 0) return null;
          return (
            <div key={section.title}>
              {isExpanded && (
                <div
                  onClick={() => toggleSection(section.title)}
                  style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '6px 10px', cursor: 'pointer', userSelect: 'none',
                    borderRadius: 4,
                  }}
                >
                  <span style={{ fontSize: 9, fontWeight: 700, color: '#4a4f63', textTransform: 'uppercase', letterSpacing: 1 }}>
                    {section.title}
                  </span>
                  <span style={{ fontSize: 9, color: '#4a4f63', transform: collapsedSections.has(section.title) ? 'rotate(-90deg)' : 'rotate(0deg)', transition: 'transform 0.12s' }}>▼</span>
                </div>
              )}

              {!collapsedSections.has(section.title) && filteredItems.map(({ to, label, icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === '/'}
                  style={({ isActive }) => ({
                    display: 'flex', flexDirection: 'column', gap: 1,
                    padding: isExpanded ? '7px 10px' : '10px 0',
                    alignItems: isExpanded ? 'stretch' : 'center',
                    borderRadius: 6,
                    color: isActive ? '#fff' : '#7c8299',
                    background: isActive ? '#7c3aed' : 'transparent',
                    textDecoration: 'none', transition: 'all 0.12s ease',
                    whiteSpace: 'nowrap',
                    minHeight: 36,
                    marginBottom: 1,
                  })}
                  onMouseEnter={e => { if (!(e.currentTarget as HTMLElement).style.background) e.currentTarget.style.background = '#252836'; }}
                  onMouseLeave={e => { if (!(e.currentTarget as HTMLElement).style.background) e.currentTarget.style.background = 'transparent'; }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{ fontSize: 14, flexShrink: 0 }}>{icon}</span>
                    {isExpanded && <span style={{ fontSize: 12, fontWeight: 600 }}>{label}</span>}
                  </div>
                </NavLink>
              ))}
            </div>
          );
        })}

        {/* Favorites */}
        {isExpanded && !navFilter.trim() && favInvestigations.length > 0 && (
          <div style={{ marginTop: 8 }}>
            <div style={{ padding: '6px 10px' }}>
              <span style={{ fontSize: 9, fontWeight: 700, color: '#4a4f63', textTransform: 'uppercase', letterSpacing: 1 }}>
                Pinned
              </span>
            </div>
            {favInvestigations.slice(0, 5).map(r => (
              <div
                key={r.targetId}
                onClick={() => navigate(`/target/${r.targetId}`)}
                style={{
                  padding: '5px 10px', cursor: 'pointer', borderRadius: 4,
                  color: '#7c8299', fontSize: 11, display: 'flex', alignItems: 'center', gap: 6,
                  transition: 'all 0.12s',
                }}
                onMouseEnter={e => { e.currentTarget.style.background = '#252836'; e.currentTarget.style.color = '#e0e0e0'; }}
                onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#7c8299'; }}
              >
                <span>📌</span>
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{r.targetName}</span>
              </div>
            ))}
          </div>
        )}

        {/* Recent Investigations */}
        {isExpanded && !navFilter.trim() && recentOnly.length > 0 && (
          <div style={{ marginTop: 8 }}>
            <div style={{ padding: '6px 10px' }}>
              <span style={{ fontSize: 9, fontWeight: 700, color: '#4a4f63', textTransform: 'uppercase', letterSpacing: 1 }}>
                Recent
              </span>
            </div>
            {recentOnly.slice(0, 5).map(r => (
              <div
                key={r.targetId}
                onClick={() => navigate(`/target/${r.targetId}`)}
                style={{
                  padding: '5px 10px', cursor: 'pointer', borderRadius: 4,
                  color: '#7c8299', fontSize: 11, display: 'flex', alignItems: 'center', gap: 6,
                  transition: 'all 0.12s',
                }}
                onMouseEnter={e => { e.currentTarget.style.background = '#252836'; e.currentTarget.style.color = '#e0e0e0'; }}
                onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#7c8299'; }}
              >
                <span>📁</span>
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{r.targetName}</span>
              </div>
            ))}
          </div>
        )}
      </nav>

      {/* Bottom controls */}
      <div style={{
        borderTop: '1px solid #2a2e3d',
        padding: isExpanded ? '8px' : '6px 0',
        flexShrink: 0, display: 'flex',
        justifyContent: isExpanded ? 'space-between' : 'center',
        alignItems: 'center',
      }}>
        {/* AI Copilot toggle */}
        <button
          onClick={() => setAssistantOpen(!assistantOpen)}
          style={{
            ...btnSmallStyle,
            color: assistantOpen ? '#a78bfa' : '#7c8299',
            fontSize: isExpanded ? 12 : 16,
            display: 'flex', alignItems: 'center', gap: 6,
            padding: isExpanded ? '4px 10px' : '4px 6px',
          }}
          onMouseEnter={e => { e.currentTarget.style.color = '#fff'; }}
          onMouseLeave={e => { e.currentTarget.style.color = assistantOpen ? '#a78bfa' : '#7c8299'; }}
        >
          <span>🧠</span>
          {isExpanded && <span style={{ fontWeight: 600 }}>AI Copilot</span>}
        </button>

        <button
          onClick={toggleSidebar}
          style={btnSmallStyle}
          onMouseEnter={e => { e.currentTarget.style.color = '#7c8299'; }}
          onMouseLeave={e => { e.currentTarget.style.color = '#4a4f63'; }}
        >
          {isExpanded ? '◀' : '▶'}
        </button>
      </div>
    </aside>
  );
}

export function MobileBottomBar() {
  const mainTabs: NavItem[] = [
    { to: '/', label: 'Mission', icon: '◈' },
    { to: '/actions', label: 'Actions', icon: '▶' },
    { to: '/insights', label: 'Insights', icon: '◎' },
    { to: '/history', label: 'History', icon: '☰' },
    { to: '/radar', label: 'Radar', icon: '◎' },
  ];

  return (
    <nav style={{
      display: 'flex', alignItems: 'stretch', height: 56,
      background: '#1a1d29', borderTop: '1px solid #2a2e3d',
      flexShrink: 0,
    }}>
      {mainTabs.map(({ to, label, icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          style={({ isActive }) => ({
            flex: 1, display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center', gap: 2,
            color: isActive ? '#7c3aed' : '#7c8299',
            textDecoration: 'none',
            fontSize: 9, fontWeight: isActive ? 700 : 500,
            minHeight: 56,
          })}
        >
          <span style={{ fontSize: 18 }}>{icon}</span>
          <span>{label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
