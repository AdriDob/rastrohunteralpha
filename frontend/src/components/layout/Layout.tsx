import { NavLink, Outlet } from 'react-router-dom';

interface NavGroup {
  stage: string;
  items: { to: string; label: string; icon: string }[];
}

const groups: NavGroup[] = [
  {
    stage: 'SCOUT',
    items: [
      { to: '/', label: 'Mission Control', icon: '◈' },
      { to: '/radar', label: 'Opportunity Radar', icon: '◎' },
    ],
  },
  {
    stage: 'MAP',
    items: [
      { to: '/hot-paths', label: 'Hot Paths', icon: '⚡' },
      { to: '/surface', label: 'Attack Surface', icon: '◉' },
    ],
  },
  {
    stage: 'HUNT',
    items: [
      { to: '/hypotheses', label: 'Hypothesis Queue', icon: '⟐' },
      { to: '/pipeline', label: 'Findings Pipeline', icon: '▤' },
    ],
  },
  {
    stage: 'BAG',
    items: [
      { to: '/evidence', label: 'Evidence Center', icon: '◈' },
    ],
  },
  {
    stage: 'REPORT',
    items: [
      { to: '/reports', label: 'Report Center', icon: '▣' },
    ],
  },
];

export default function Layout() {
  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      <aside style={{
        width: 220, background: '#1a1d29', borderRight: '1px solid #2a2e3d',
        display: 'flex', flexDirection: 'column', flexShrink: 0,
      }}>
        <div style={{
          padding: '16px 20px', borderBottom: '1px solid #2a2e3d',
          display: 'flex', alignItems: 'center', gap: 10,
        }}>
          <div style={{
            width: 32, height: 32, borderRadius: 6,
            background: 'linear-gradient(135deg,#7c3aed,#a855f7)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#fff', fontWeight: 800, fontSize: 14,
          }}>R</div>
          <span style={{ fontWeight: 800, fontSize: 16, letterSpacing: 2, color: '#fff' }}>RASTRO</span>
        </div>
        <nav style={{ flex: 1, padding: '12px 8px', display: 'flex', flexDirection: 'column', gap: 6, overflowY: 'auto' }}>
          {groups.map((group) => (
            <div key={group.stage}>
              <div style={{
                fontSize: 10, fontWeight: 700, color: '#4a4f63',
                padding: '8px 14px 4px', letterSpacing: 1.5,
              }}>
                {group.stage}
              </div>
              {group.items.map(({ to, label, icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === '/'}
                  style={({ isActive }) => ({
                    display: 'flex', alignItems: 'center', gap: 10,
                    padding: '8px 14px', borderRadius: 6,
                    fontSize: 13, fontWeight: 500,
                    color: isActive ? '#fff' : '#7c8299',
                    background: isActive ? '#7c3aed' : 'transparent',
                    textDecoration: 'none', transition: 'all 0.15s',
                  })}
                >
                  <span style={{ fontSize: 14 }}>{icon}</span>
                  <span>{label}</span>
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
      </aside>
      <main style={{ flex: 1, overflow: 'auto', padding: '24px 32px' }}>
        <Outlet />
      </main>
    </div>
  );
}
