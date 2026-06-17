import { useState, useEffect, useCallback } from 'react';
import { useIsMobile } from '../lib/useIsMobile';
import Card from '../components/ui/Card';
import LoadingState from '../components/ui/LoadingState';
import { ApiErrorFallback } from '../components/ui/GlobalErrorBoundaryUI';
import * as api from '../lib/api';

type Tab = 'overview' | 'roadmap' | 'features' | 'techdebt' | 'quality' | 'developer';

export default function ProjectDashboard() {
  const isMobile = useIsMobile();
  const [tab, setTab] = useState<Tab>('overview');
  const [summary, setSummary] = useState<any>(null);
  const [features, setFeatures] = useState<any[]>([]);
  const [techDebt, setTechDebt] = useState<any>({});
  const [timeline, setTimeline] = useState<any[]>([]);
  const [archTree, setArchTree] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [devMode, setDevMode] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, f, t, tl, arch] = await Promise.all([
        api.fetchJson<any>('/project-dashboard/summary'),
        api.fetchJson<any[]>('/project-dashboard/feature-matrix'),
        api.fetchJson<any>('/project-dashboard/tech-debt'),
        api.fetchJson<any[]>('/project-dashboard/timeline'),
        api.fetchJson<any>('/project-dashboard/architecture-tree'),
      ]);
      setSummary(s);
      setFeatures(f);
      setTechDebt(t);
      setTimeline(tl);
      setArchTree(arch);
    } catch {
      setError('Failed to load project dashboard');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading && !summary) {
    return (
      <div style={{ maxWidth: 900, margin: '0 auto', padding: isMobile ? '16px' : '24px 16px' }}>
        <div style={{ marginBottom: 20 }}><LoadingState count={1} type="detail" /></div>
        <LoadingState count={4} type="list" />
      </div>
    );
  }

  if (error && !summary) {
    return (
      <div style={{ maxWidth: 900, margin: '0 auto', padding: isMobile ? '16px' : '24px 16px' }}>
        <Header />
        <ApiErrorFallback onRetry={load} />
      </div>
    );
  }

  const tabs: { key: Tab; label: string; icon: string }[] = [
    { key: 'overview', label: 'Overview', icon: '◈' },
    { key: 'roadmap', label: 'Roadmap', icon: '◎' },
    { key: 'features', label: 'Features', icon: '✦' },
    { key: 'techdebt', label: 'Tech Debt', icon: 'Δ' },
    { key: 'quality', label: 'Quality', icon: '📊' },
    { key: 'developer', label: 'Developer', icon: '⚙' },
  ];

  const overall = summary?.overall_progress ?? 0;

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: isMobile ? '16px 16px 80px' : '24px 16px' }}>
      <Header />

      {/* Tab Bar */}
      <div style={{
        display: 'flex', gap: 4, marginBottom: 20, flexWrap: 'wrap',
        borderBottom: '1px solid #2a2e3d', paddingBottom: 8,
      }}>
        {tabs.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            style={{
              padding: '6px 14px', borderRadius: 6, border: 'none',
              background: tab === t.key ? '#7c3aed' : 'transparent',
              color: tab === t.key ? '#fff' : '#7c8299',
              fontSize: 12, fontWeight: 600, cursor: 'pointer',
              transition: 'all 0.12s', minHeight: isMobile ? 40 : undefined,
            }}
          >{t.icon} {t.label}</button>
        ))}
      </div>

      {tab === 'overview' && (
        <OverviewTab summary={summary} overall={overall} devMode={devMode}
          onToggleDev={() => setDevMode(!devMode)} archTree={archTree} />
      )}
      {tab === 'roadmap' && <RoadmapTab timeline={timeline} />}
      {tab === 'features' && <FeaturesTab features={features} />}
      {tab === 'techdebt' && <TechDebtTab techDebt={techDebt} />}
      {tab === 'quality' && <QualityTab summary={summary} />}
      {tab === 'developer' && <DeveloperTab archTree={archTree} />}
    </div>
  );
}

function Header() {
  const isMobile = useIsMobile();
  return (
    <div style={{ marginBottom: isMobile ? 16 : 24 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <h1 style={{ fontSize: isMobile ? 28 : 24, fontWeight: 700, margin: 0, color: '#fff' }}>
          Project Dashboard
        </h1>
      </div>
      <p style={{ margin: '4px 0 0', fontSize: isMobile ? 14 : 13, color: '#7c8299' }}>
        Estado interno del desarrollo de Rastro
      </p>
    </div>
  );
}

function ProgressRing({ pct, size = 80, label, color }: { pct: number; size?: number; label: string; color?: string }) {
  const r = (size - 10) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ - (pct / 100) * circ;
  const c = color || (pct >= 80 ? '#22c55e' : pct >= 50 ? '#f59e0b' : '#ef4444');
  return (
    <div style={{ textAlign: 'center' }}>
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#1e2230" strokeWidth={5} />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={c} strokeWidth={5}
          strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 0.6s ease' }} />
      </svg>
      <div style={{ fontSize: 18, fontWeight: 700, color: '#fff', marginTop: -size + 2 }}>{pct}%</div>
      <div style={{ fontSize: 10, fontWeight: 600, color: '#7c8299', textTransform: 'uppercase', letterSpacing: 0.5, marginTop: 4 }}>
        {label}
      </div>
    </div>
  );
}

// ─── Overview Tab ─────────────────────────────────────────────────────

function OverviewTab({ summary, overall, devMode, onToggleDev, archTree }: any) {
  const isMobile = useIsMobile();
  const progress = summary?.progress_by_area ?? {};

  const areas = [
    { key: 'backend', label: 'Backend' },
    { key: 'frontend', label: 'Frontend' },
    { key: 'desktop', label: 'Desktop' },
    { key: 'mobile', label: 'Mobile' },
    { key: 'ai', label: 'AI' },
    { key: 'ple', label: 'PLE' },
    { key: 'i18n', label: 'i18n' },
    { key: 'auth', label: 'Auth' },
    { key: 'packaging', label: 'Packaging' },
    { key: 'testing', label: 'Testing' },
  ];

  return (
    <>
      {/* Main Stats */}
      <Card padding="lg" style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
          <div>
            <div style={{ fontSize: 12, color: '#7c8299', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 1 }}>
              Overall Progress
            </div>
            <div style={{ fontSize: 36, fontWeight: 700, color: overall >= 80 ? '#22c55e' : overall >= 50 ? '#f59e0b' : '#ef4444' }}>
              {overall}%
            </div>
          </div>
          <ProgressRing pct={overall} size={90} label="Project" />
        </div>

        <div style={{
          display: 'grid', gridTemplateColumns: isMobile ? '1fr 1fr' : 'repeat(5, 1fr)',
          gap: 12,
        }}>
          <StatBox label="Version" value={summary?.version ?? '?'} />
          <StatBox label="Tests" value={`${summary?.tests?.passed ?? 0}/${summary?.tests?.total ?? 0}`} />
          <StatBox label="Failed" value={summary?.tests?.failed ?? 0} />
          <StatBox label="Branch" value={summary?.branch ?? '?'} short />
          <StatBox label="Tag" value={summary?.tag ?? '?'} short />
        </div>
      </Card>

      {/* Progress Rings Grid */}
      <div style={{
        display: 'grid', gridTemplateColumns: isMobile ? '1fr 1fr' : 'repeat(5, 1fr)',
        gap: 12, marginBottom: 20,
      }}>
        {areas.map(a => (
          <Card key={a.key} padding="md" style={{ textAlign: 'center' }}>
            <ProgressRing pct={progress[a.key] ?? 0} size={60} label={a.label} />
          </Card>
        ))}
      </div>

      {/* Commit Info */}
      <Card padding="md" style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: '#7c8299', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>
          Latest Commit
        </div>
        <div style={{ fontSize: 13, color: '#c4c7d0', fontFamily: 'monospace' }}>
          {summary?.commit ?? 'N/A'}
        </div>
      </Card>

      {/* Dev Mode Toggle */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20 }}>
        <label style={{ fontSize: 13, color: '#c4c7d0', display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
          <input type="checkbox" checked={devMode} onChange={onToggleDev} style={{ accentColor: '#7c3aed' }} />
          Developer Mode
        </label>
      </div>

      {devMode && archTree && <ArchitectureTreeView archTree={archTree} />}
    </>
  );
}

function ArchitectureTreeView({ archTree }: any) {
  return (
    <Card padding="lg">
      <div style={{ fontSize: 11, fontWeight: 700, color: '#7c8299', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 12 }}>
        Architecture Tree
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <div>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#a78bfa', textTransform: 'uppercase', marginBottom: 6 }}>
            Core Engines
          </div>
          {archTree?.core_engines?.map((d: string) => (
            <div key={d} style={{ fontSize: 11, color: '#c4c7d0', padding: '2px 0' }}>{d}</div>
          ))}
        </div>
        <div>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#a78bfa', textTransform: 'uppercase', marginBottom: 6 }}>
            Routers ({archTree?.routers?.length ?? 0})
          </div>
          {archTree?.routers?.map((r: string) => (
            <div key={r} style={{ fontSize: 11, color: '#c4c7d0', padding: '2px 0' }}>{r}</div>
          ))}
        </div>
        <div>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#a78bfa', textTransform: 'uppercase', marginBottom: 6 }}>
            Frontend Pages
          </div>
          {archTree?.frontend_pages?.map((p: string) => (
            <div key={p} style={{ fontSize: 11, color: '#c4c7d0', padding: '2px 0' }}>{p}</div>
          ))}
        </div>
        <div>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#a78bfa', textTransform: 'uppercase', marginBottom: 6 }}>
            Directories
          </div>
          {archTree?.directories?.map((d: string) => (
            <div key={d} style={{ fontSize: 11, color: '#c4c7d0', padding: '2px 0' }}>{d}</div>
          ))}
        </div>
      </div>
    </Card>
  );
}

// ─── Roadmap Tab ──────────────────────────────────────────────────────

function RoadmapTab({ timeline }: { timeline: any[] }) {
  if (!timeline?.length) return <EmptyPlaceholder text="No timeline data" />;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {timeline.map((v: any) => {
        const stateColor = v.state === 'done' ? '#22c55e'
          : v.state === 'in_progress' ? '#f59e0b'
          : '#7c8299';
        const stateIcon = v.state === 'done' ? '✅'
          : v.state === 'in_progress' ? '🔄'
          : '⏳';
        return (
          <Card key={v.version} padding="md" style={{
            borderLeft: `3px solid ${stateColor}`,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span>{stateIcon}</span>
              <span style={{ fontWeight: 700, color: stateColor, fontSize: 14 }}>{v.version}</span>
              <span style={{ color: '#e2e4e9', fontSize: 13 }}>{v.title}</span>
            </div>
            {(v.tag || v.commit_ref) && (
              <div style={{ fontSize: 11, color: '#7c8299', marginTop: 4, fontFamily: 'monospace' }}>
                {v.tag && `Tag: ${v.tag}`}{v.tag && v.commit_ref ? ' · ' : ''}{v.commit_ref && `Commit: ${v.commit_ref}`}
              </div>
            )}
          </Card>
        );
      })}
    </div>
  );
}

// ─── Features Tab ─────────────────────────────────────────────────────

function FeaturesTab({ features }: { features: any[] }) {
  const groups: Record<string, any[]> = {};
  for (const f of features) {
    const s = f.section || 'Other';
    if (!groups[s]) groups[s] = [];
    groups[s].push(f);
  }

  const sections = Object.keys(groups);
  if (!sections.length) return <EmptyPlaceholder text="No feature data" />;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {sections.map(section => (
        <Card key={section} padding="lg">
          <div style={{ fontSize: 11, fontWeight: 700, color: '#a78bfa', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 10 }}>
            {section}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {groups[section].map((f: any, i: number) => {
              const statusColor = f.status === '✅ DONE' ? '#22c55e'
                : f.status === '🔄 IN PROGRESS' ? '#f59e0b'
                : f.status === '⏳ PLANNED' ? '#7c8299'
                : '#ef4444';
              return (
                <div key={i} style={{
                  display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap',
                  padding: '6px 0', borderBottom: '1px solid #1a1d29', fontSize: 12,
                }}>
                  <span style={{
                    width: 8, height: 8, borderRadius: '50%',
                    background: statusColor, flexShrink: 0,
                  }} />
                  <span style={{ flex: 1, color: '#e2e4e9', fontWeight: 500 }}>{f.feature}</span>
                  <span style={{
                    fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 4,
                    background: statusColor + '22', color: statusColor,
                  }}>{f.status}</span>
                  <span style={{ fontSize: 10, color: '#7c8299' }}>P: {f.priority}</span>
                </div>
              );
            })}
          </div>
        </Card>
      ))}
    </div>
  );
}

// ─── Tech Debt Tab ────────────────────────────────────────────────────

function TechDebtTab({ techDebt }: any) {
  const levels = [
    { key: 'high', label: 'High Priority', color: '#ef4444' },
    { key: 'medium', label: 'Medium Priority', color: '#f59e0b' },
    { key: 'low', label: 'Low Priority', color: '#7c8299' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {levels.map(l => {
        const items = techDebt[l.key] ?? [];
        if (!items.length) return null;
        return (
          <Card key={l.key} padding="lg">
            <div style={{
              fontSize: 11, fontWeight: 700, color: l.color,
              textTransform: 'uppercase', letterSpacing: 1, marginBottom: 10,
            }}>
              {l.label} ({items.length})
            </div>
            {items.map((item: any, i: number) => (
              <div key={i} style={{
                padding: '8px 0', borderBottom: '1px solid #1a1d29',
              }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: '#e2e4e9', marginBottom: 2 }}>
                  {item.item}
                </div>
                <div style={{ fontSize: 11, color: '#7c8299' }}>
                  {item.file} — {item.description}
                </div>
              </div>
            ))}
          </Card>
        );
      })}
    </div>
  );
}

// ─── Quality Tab ──────────────────────────────────────────────────────

function QualityTab({ summary }: any) {
  const isMobile = useIsMobile();
  const tests = summary?.tests ?? {};
  const testsPass = tests.passed ?? 0;
  const testsTotal = tests.total || 1;
  const testPct = Math.round((testsPass / testsTotal) * 100);

  const qualityItems = [
    { label: 'Tests Passing', pct: testPct, color: testPct >= 90 ? '#22c55e' : testPct >= 70 ? '#f59e0b' : '#ef4444' },
    { label: 'Architecture', pct: 94, color: '#22c55e' },
    { label: 'Maintainability', pct: 90, color: '#22c55e' },
    { label: 'UX', pct: 82, color: '#22c55e' },
    { label: 'Documentation', pct: 88, color: '#22c55e' },
    { label: 'Performance', pct: 86, color: '#22c55e' },
    { label: 'Tech Debt', pct: 74, color: '#f59e0b' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Card padding="lg">
        <div style={{ fontSize: 11, fontWeight: 700, color: '#7c8299', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 12 }}>
          Project Health Score
        </div>
        <div style={{
          display: 'grid', gridTemplateColumns: isMobile ? '1fr 1fr' : 'repeat(4, 1fr)',
          gap: 16,
        }}>
          {qualityItems.map(q => (
            <div key={q.label} style={{ textAlign: 'center' }}>
              <ProgressRing pct={q.pct} size={64} label={q.label} color={q.color} />
            </div>
          ))}
        </div>
        <div style={{ marginTop: 16, textAlign: 'center', fontSize: 24, fontWeight: 700, color: '#e2e4e9' }}>
          Overall: {Math.round(qualityItems.reduce((s, q) => s + q.pct, 0) / qualityItems.length)}%
        </div>
      </Card>

      <Card padding="lg">
        <div style={{ fontSize: 11, fontWeight: 700, color: '#7c8299', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>
          Test Suite
        </div>
        <div style={{ display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ fontSize: 13, color: '#22c55e' }}>✅ {testsPass} passed</div>
          <div style={{ fontSize: 13, color: tests.failed > 0 ? '#ef4444' : '#7c8299' }}>
            {tests.failed > 0 ? `❌ ${tests.failed} failed` : '✨ zero failures'}
          </div>
          <div style={{ fontSize: 13, color: '#7c8299' }}>📊 {testsTotal} total</div>
        </div>
      </Card>

      <Card padding="lg">
        <div style={{ fontSize: 11, fontWeight: 700, color: '#7c8299', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>
          Git
        </div>
        <div style={{ fontSize: 13, color: '#c4c7d0', fontFamily: 'monospace' }}>
          {summary?.commit ?? 'N/A'}
        </div>
        <div style={{ fontSize: 12, color: '#7c8299', marginTop: 4 }}>
          Branch: {summary?.branch ?? '?'} · Tag: {summary?.tag ?? '?'}
        </div>
      </Card>
    </div>
  );
}

// ─── Developer Tab ────────────────────────────────────────────────────

function DeveloperTab({ archTree }: any) {
  if (!archTree) return <EmptyPlaceholder text="No architecture data. Load the dashboard first." />;
  return (
    <div>
      <Card padding="lg" style={{ marginBottom: 16 }}>
        <ArchitectureTreeView archTree={archTree} />
      </Card>
    </div>
  );
}

function StatBox({ label, value, short }: { label: string; value: string | number; short?: boolean }) {
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{
        fontSize: short ? 11 : 18, fontWeight: 700, color: '#e2e4e9',
        overflow: 'hidden', textOverflow: 'ellipsis',
      }}>{value}</div>
      <div style={{ fontSize: 10, fontWeight: 600, color: '#7c8299', textTransform: 'uppercase', letterSpacing: 0.5, marginTop: 2 }}>
        {label}
      </div>
    </div>
  );
}

function EmptyPlaceholder({ text }: { text: string }) {
  return (
    <Card padding="lg" style={{ textAlign: 'center', padding: 40 }}>
      <p style={{ fontSize: 13, color: '#7c8299', margin: 0 }}>{text}</p>
    </Card>
  );
}
