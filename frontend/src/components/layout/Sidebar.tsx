import { useState, useMemo } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useUI } from '../../lib/store';
import { useTheme } from '../../lib/theme';
import { useI18n } from '../../lib/i18n';
import type { Translations } from '../../lib/i18n';
import NotificationsDropdown from '../NotificationsDropdown';
import { useTargetsDTO } from '../../lib/query';

interface NavItem {
  to: string;
  labelKey: keyof Translations;
  icon: string;
}

interface NavSection {
  titleKey: keyof Translations;
  items: NavItem[];
}

const collapsedWidth = 56;
const expandedWidth = 200;

const btnSmallStyle: React.CSSProperties = {
  background: 'transparent', border: 'none', color: '#7c8299', cursor: 'pointer',
  fontSize: 14, padding: '4px 6px', borderRadius: 4,
};

export function DesktopSidebar({ isExpanded }: { isExpanded: boolean }) {
  const { toggleSidebar, recentInvestigations, favoriteTargets, assistantOpen, setAssistantOpen } = useUI();
  const { theme, setTheme } = useTheme();
  const { t, lang, setLang } = useI18n();
  const navigate = useNavigate();

  const navSections: (NavSection & { submenus?: { labelKey: keyof Translations; icon: string; items: NavItem[] }[] })[] = [
    {
      titleKey: 'nav_mission',
      items: [
        { to: '/', labelKey: 'mission_control', icon: '◈' },
        { to: '/investigations', labelKey: 'investigations', icon: '◈' },
        { to: '/daily', labelKey: 'daily_briefing', icon: '🌅' },
      ],
    },
    {
      titleKey: 'nav_findings',
      items: [
        { to: '/pipeline', labelKey: 'pipeline', icon: '▤' },
        { to: '/hypothesis', labelKey: 'hypotheses', icon: '⟐' },
      ],
      submenus: [
        {
          labelKey: 'evidence_center' as keyof Translations,
          icon: '📋',
          items: [
            { to: '/evidence', labelKey: 'evidence_center', icon: '📋' },
            { to: '/replay', labelKey: 'replay_center', icon: '🔄' },
            { to: '/screenshots', labelKey: 'screenshots', icon: '🖼️' },
          ],
        },
        {
          labelKey: 'attack_surface' as keyof Translations,
          icon: '◉',
          items: [
            { to: '/surface', labelKey: 'attack_surface', icon: '◉' },
            { to: '/hotpaths', labelKey: 'hot_paths', icon: '⚡' },
          ],
        },
      ],
    },
    {
      titleKey: 'nav_analysis',
      items: [
        { to: '/insights', labelKey: 'key_insights', icon: '◎' },
      ],
      submenus: [
        {
          labelKey: 'confidence_dashboard' as keyof Translations,
          icon: '📊',
          items: [
            { to: '/confidence', labelKey: 'confidence_dashboard', icon: '📊' },
            { to: '/differential', labelKey: 'differential', icon: 'Δ' },
          ],
        },
        {
          labelKey: 'ai_intelligence' as keyof Translations,
          icon: '🧠',
          items: [
            { to: '/intelligence', labelKey: 'ai_intelligence', icon: '🧠' },
            { to: '/personal-intelligence', labelKey: 'personal_intelligence', icon: '📊' },
          ],
        },
      ],
    },
    {
      titleKey: 'nav_operations',
      items: [
        { to: '/agents', labelKey: 'agent_center', icon: '🤖' },
        { to: '/executive-dashboard', labelKey: 'executive_dashboard', icon: '📊' },
        { to: '/pipeline-monitor', labelKey: 'pipeline_monitor', icon: '⚙' },
      ],
      submenus: [
        {
          labelKey: 'operations_dashboard' as keyof Translations,
          icon: '⚙',
          items: [
            { to: '/operations', labelKey: 'operations_dashboard', icon: '⚙' },
            { to: '/tasks', labelKey: 'task_queue', icon: '✓' },
            { to: '/history', labelKey: 'history_view', icon: '☰' },
          ],
        },
      ],
    },
    {
      titleKey: 'nav_intelligence',
      items: [
        { to: '/agents', labelKey: 'agent_center', icon: '🤖' },
        { to: '/executive-dashboard', labelKey: 'executive_dashboard', icon: '📊' },
        { to: '/radar', labelKey: 'opportunity_radar', icon: '◎' },
        { to: '/programs', labelKey: 'program_catalog', icon: '📋' },
        { to: '/reports', labelKey: 'report_center', icon: '📄' },
        { to: '/reports/history', labelKey: 'report_history', icon: '📋' },
        { to: '/project-dashboard', labelKey: 'project_dashboard', icon: '◈' },
        { to: '/identity-center', labelKey: 'identity_center', icon: '🔐' },
        { to: '/settings', labelKey: 'settings', icon: '⚙' },
      ],
    },
  ];
  const [collapsedSections, setCollapsedSections] = useState<Set<string>>(new Set());
  const [navFilter, setNavFilter] = useState('');
  const { data: allTargets } = useTargetsDTO();
  const validTargetIds = useMemo(() => {
    if (!allTargets) return null;
    return new Set(allTargets.items.map((t: { id: number }) => t.id));
  }, [allTargets]);

  const reconciledFavorites = useMemo(() => {
    if (!validTargetIds) return favoriteTargets;
    return favoriteTargets.filter(id => validTargetIds.has(id));
  }, [favoriteTargets, validTargetIds]);

  const reconciledRecent = useMemo(() => {
    if (!validTargetIds) return recentInvestigations;
    return recentInvestigations.filter(r => validTargetIds.has(r.targetId));
  }, [recentInvestigations, validTargetIds]);

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

  const favInvestigations = reconciledRecent.filter(r => reconciledFavorites.includes(r.targetId));
  const recentOnly = reconciledRecent.filter(r => !reconciledFavorites.includes(r.targetId));

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
          const sectionLabel = t[section.titleKey];
          const filteredItems = section.items.filter(i => filterMatches(t[i.labelKey]));
          const hasVisibleSubmenus = section.submenus?.some(sm =>
            sm.items.some(i => filterMatches(t[i.labelKey]))
          );
          if (navFilter.trim() && filteredItems.length === 0 && !hasVisibleSubmenus) return null;
          return (
            <div key={section.titleKey}>
              {isExpanded && (
                <div
                  onClick={() => toggleSection(section.titleKey)}
                  style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '6px 10px', cursor: 'pointer', userSelect: 'none',
                    borderRadius: 4,
                  }}
                >
                  <span style={{ fontSize: 9, fontWeight: 700, color: '#4a4f63', textTransform: 'uppercase', letterSpacing: 1 }}>
                    {sectionLabel}
                  </span>
                  <span style={{ fontSize: 9, color: '#4a4f63', transform: collapsedSections.has(section.titleKey) ? 'rotate(-90deg)' : 'rotate(0deg)', transition: 'transform 0.12s' }}>▼</span>
                </div>
              )}

              {!collapsedSections.has(section.titleKey) && (
                <>
                  {filteredItems.map(({ to, labelKey, icon }) => (
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
                        {isExpanded && <span style={{ fontSize: 12, fontWeight: 600 }}>{t[labelKey]}</span>}
                      </div>
                    </NavLink>
                  ))}
                  {/* Submenus */}
                  {isExpanded && section.submenus?.map(sm => {
                    const filteredSm = sm.items.filter(i => filterMatches(t[i.labelKey]));
                    if (navFilter.trim() && filteredSm.length === 0) return null;
                    const subKey = `${section.titleKey}_${sm.labelKey}`;
                    const isCollapsed = collapsedSections.has(subKey);
                    return (
                      <div key={subKey} style={{ marginLeft: 8 }}>
                        <div
                          onClick={() => toggleSection(subKey)}
                          style={{
                            display: 'flex', alignItems: 'center', gap: 6,
                            padding: '5px 10px', cursor: 'pointer', borderRadius: 4,
                            fontSize: 10, color: '#4a4f63', fontWeight: 600,
                          }}
                        >
                          <span style={{ fontSize: 12 }}>{sm.icon}</span>
                          <span style={{ flex: 1 }}>{t[sm.labelKey]}</span>
                          <span style={{ fontSize: 8, transform: isCollapsed ? 'rotate(-90deg)' : 'rotate(0deg)', transition: 'transform 0.12s' }}>▼</span>
                        </div>
                        {!isCollapsed && filteredSm.map(({ to, labelKey, icon }) => (
                          <NavLink
                            key={to}
                            to={to}
                            style={({ isActive }) => ({
                              display: 'flex', alignItems: 'center', gap: 8,
                              padding: '5px 10px', marginLeft: 4,
                              borderRadius: 4, fontSize: 11,
                              color: isActive ? '#fff' : '#7c8299',
                              background: isActive ? '#7c3aed' : 'transparent',
                              textDecoration: 'none', transition: 'all 0.12s ease',
                              whiteSpace: 'nowrap',
                            })}
                            onMouseEnter={e => { if (!(e.currentTarget as HTMLElement).style.background) e.currentTarget.style.background = '#252836'; }}
                            onMouseLeave={e => { if (!(e.currentTarget as HTMLElement).style.background) e.currentTarget.style.background = 'transparent'; }}
                          >
                            <span style={{ fontSize: 12 }}>{icon}</span>
                            <span>{t[labelKey]}</span>
                          </NavLink>
                        ))}
                      </div>
                    );
                  })}
                </>
              )}
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
  const { t } = useI18n();
  const mainTabs: NavItem[] = [
    { to: '/', labelKey: 'mission_control', icon: '◈' },
    { to: '/investigations', labelKey: 'investigations', icon: '◈' },
    { to: '/evidence', labelKey: 'evidence_center', icon: '📋' },
    { to: '/reports', labelKey: 'report_center', icon: '📄' },
    { to: '/settings', labelKey: 'settings', icon: '⚙' },
  ];

  return (
    <nav style={{
      display: 'flex', alignItems: 'stretch', height: 56,
      background: '#1a1d29', borderTop: '1px solid #2a2e3d',
      flexShrink: 0,
    }}>
      {mainTabs.map(({ to, labelKey, icon }) => (
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
          <span>{t[labelKey]}</span>
        </NavLink>
      ))}
    </nav>
  );
}
