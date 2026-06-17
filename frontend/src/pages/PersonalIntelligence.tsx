import { useState, useEffect, useCallback } from 'react';
import { useIsMobile } from '../lib/useIsMobile';
import Card from '../components/ui/Card';
import LoadingState from '../components/ui/LoadingState';
import { ApiErrorFallback } from '../components/ui/GlobalErrorBoundaryUI';
import * as api from '../lib/api';

export default function PersonalIntelligence() {
  const isMobile = useIsMobile();
  const [profile, setProfile] = useState<any>(null);
  const [events, setEvents] = useState<any[]>([]);
  const [recommendations, setRecommendations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [adaptiveMode, setAdaptiveMode] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [prof, evts, recs] = await Promise.all([
        api.getLearningProfile(),
        api.getLearningEvents(),
        api.getDailyRecommendations(),
      ]);
      setProfile(prof);
      setEvents(evts);
      setRecommendations(recs);
      if (prof.exists) setAdaptiveMode(prof.adaptive_mode ?? true);
    } catch {
      setError('Failed to load learning profile');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const toggleAdaptive = async () => {
    const next = !adaptiveMode;
    try {
      await api.updateLearningPreferences({ adaptive_mode: next });
      setAdaptiveMode(next);
    } catch {}
  };

  const handleReset = async () => {
    try {
      await api.resetLearningProfile();
      await load();
    } catch {}
  };

  const handleExport = async (fmt: 'json' | 'markdown') => {
    try {
      const data = await api.exportLearningProfile(fmt);
      const blob = fmt === 'json'
        ? new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
        : new Blob([data as any], { type: 'text/markdown' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `investigator-profile.${fmt}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {}
  };

  if (loading && !profile) {
    return (
      <div style={{ maxWidth: 800, margin: '0 auto', padding: isMobile ? '16px' : '24px 16px' }}>
        <div style={{ marginBottom: 20 }}><LoadingState count={1} type="detail" /></div>
        <LoadingState count={3} type="list" />
      </div>
    );
  }

  if (error && !profile) {
    return (
      <div style={{ maxWidth: 800, margin: '0 auto', padding: isMobile ? '16px' : '24px 16px' }}>
        <Header />
        <ApiErrorFallback onRetry={load} />
      </div>
    );
  }

  const disc = profile?.discovery ?? {};
  const act = profile?.activity ?? {};
  const pref = profile?.preferences ?? {};
  const success = profile?.success_history ?? {};
  const hasProfile = profile?.exists;

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: isMobile ? '16px 16px 80px' : '24px 16px' }}>
      <Header />

      {/* Controls Bar */}
      <div style={{
        display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 20,
        alignItems: 'center',
      }}>
        <label style={{
          display: 'flex', alignItems: 'center', gap: 8,
          fontSize: 13, color: '#c4c7d0', cursor: 'pointer',
          padding: '6px 12px', borderRadius: 6,
          background: adaptiveMode ? 'rgba(124,58,237,0.15)' : 'transparent',
          border: '1px solid', borderColor: adaptiveMode ? '#7c3aed' : '#2a2e3d',
          minHeight: isMobile ? 44 : undefined,
        }}>
          <input
            type="checkbox"
            checked={adaptiveMode}
            onChange={toggleAdaptive}
            style={{ accentColor: '#7c3aed' }}
          />
          Adaptive Mode
        </label>

        <button onClick={() => handleExport('json')} style={btnStyle}>
          Export JSON
        </button>
        <button onClick={() => handleExport('markdown')} style={btnStyle}>
          Export MD
        </button>
        <button onClick={handleReset} style={{ ...btnStyle, borderColor: '#ef4444', color: '#ef4444' }}>
          Reset Profile
        </button>
      </div>

      {!hasProfile ? (
        <Card padding="lg" style={{ textAlign: 'center', padding: 40 }}>
          <div style={{ fontSize: 40, marginBottom: 12 }}>📊</div>
          <h2 style={{ fontSize: 18, fontWeight: 700, color: '#e2e4e9', margin: '0 0 8px' }}>
            No Learning Data Yet
          </h2>
          <p style={{ fontSize: 13, color: '#7c8299', maxWidth: 400, margin: '0 auto', lineHeight: 1.5 }}>
            Your investigator profile will grow as you investigate targets, create findings,
            and use the system. Enable Adaptive Mode above to start.
          </p>
        </Card>
      ) : (
        <>
          {/* Stats Grid */}
          <div style={{
            display: 'grid', gridTemplateColumns: isMobile ? '1fr 1fr' : 'repeat(4, 1fr)',
            gap: 10, marginBottom: 20,
          }}>
            <StatBox label="Targets" value={disc.total_targets ?? 0} />
            <StatBox label="Findings" value={success.confirmed_findings ?? 0} />
            <StatBox label="Hours" value={(act.total_hours_active ?? 0).toFixed(1)} />
            <StatBox label="Sessions" value={act.total_sessions ?? 0} />
          </div>

          {/* Two-column layout */}
          <div style={{
            display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr',
            gap: 16, marginBottom: 20,
          }}>
            {/* Strength Map */}
            <Card padding="lg">
              <SectionTitle>Strength Map</SectionTitle>
              {pref.favorite_bug_classes?.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {(pref.favorite_bug_classes as any[])
                    .sort((a: any, b: any) => (b.count ?? 0) - (a.count ?? 0))
                    .slice(0, 8)
                    .map((c: any, i: number) => (
                      <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div style={{
                          width: 6, height: 6, borderRadius: '50%',
                          background: i === 0 ? '#7c3aed' : i < 3 ? '#a78bfa' : '#4a4f63',
                          flexShrink: 0,
                        }} />
                        <span style={{ flex: 1, fontSize: 13, color: '#e2e4e9' }}>
                          {c.class ?? c.key ?? c.name ?? '?'}
                        </span>
                        <span style={{ fontSize: 12, color: '#7c8299', fontWeight: 600 }}>
                          {c.count}
                        </span>
                      </div>
                    ))}
                </div>
              ) : (
                <p style={{ fontSize: 12, color: '#7c8299', margin: 0 }}>
                  No bug class data yet. Create findings to build your strength map.
                </p>
              )}
            </Card>

            {/* Industries & Technologies */}
            <Card padding="lg">
              <SectionTitle>Areas of Expertise</SectionTitle>
              {disc.industries?.length > 0 ? (
                <>
                  <div style={{ marginBottom: 12 }}>
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#7c8299', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 6 }}>
                      Industries
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                      {(disc.industries as string[]).map((ind: string, i: number) => (
                        <span key={i} style={{
                          fontSize: 11, fontWeight: 600, color: '#c4c7d0',
                          background: '#1e2230', padding: '3px 8px', borderRadius: 4,
                          border: '1px solid #2a2e3d',
                        }}>{ind}</span>
                      ))}
                    </div>
                  </div>
                </>
              ) : (
                <p style={{ fontSize: 12, color: '#7c8299', margin: '0 0 12' }}>
                  No industries tracked yet.
                </p>
              )}
              {disc.technologies?.length > 0 && (
                <div>
                  <div style={{ fontSize: 10, fontWeight: 700, color: '#7c8299', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 6 }}>
                    Technologies
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {(disc.technologies as string[]).map((tech: string, i: number) => (
                      <span key={i} style={{
                        fontSize: 11, fontWeight: 600, color: '#c4c7d0',
                        background: '#1e2230', padding: '3px 8px', borderRadius: 4,
                        border: '1px solid #2a2e3d',
                      }}>{tech}</span>
                    ))}
                  </div>
                </div>
              )}
            </Card>
          </div>

          {/* Success History */}
          <Card padding="lg" style={{ marginBottom: 20 }}>
            <SectionTitle>Success History</SectionTitle>
            <div style={{
              display: 'grid', gridTemplateColumns: isMobile ? '1fr 1fr' : 'repeat(4, 1fr)',
              gap: 12,
            }}>
              <SuccessItem label="Confirmed" value={success.confirmed_findings ?? 0} color="#22c55e" />
              <SuccessItem label="High Severity" value={success.high_severity_findings ?? 0} color="#ef4444" />
              <SuccessItem label="Rejected" value={success.rejected_findings ?? 0} color="#f59e0b" />
              <SuccessItem label="Duplicates" value={success.duplicates_found ?? 0} color="#7c8299" />
            </div>
            {success.total_roi_estimate > 0 && (
              <div style={{ marginTop: 12, fontSize: 13, color: '#22c55e', fontWeight: 600 }}>
                Total ROI: ${(success.total_roi_estimate ?? 0).toLocaleString()}
              </div>
            )}
          </Card>

          {/* Daily Recommendations */}
          {recommendations.length > 0 && (
            <Card padding="lg" style={{ marginBottom: 20 }}>
              <SectionTitle>Recommendations</SectionTitle>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {recommendations.map((r: any, i: number) => (
                  <div key={i} style={{
                    padding: '10px 12px', borderRadius: 6,
                    background: '#1a1d29', border: '1px solid #2a2e3d',
                  }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: '#e2e4e9', marginBottom: 4 }}>
                      {r.message}
                    </div>
                    <div style={{ fontSize: 11, color: '#7c8299' }}>
                      {r.explanation}
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Recent Events Timeline */}
          {events.length > 0 && (
            <Card padding="lg" style={{ marginBottom: 20 }}>
              <SectionTitle>Recent Activity</SectionTitle>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {events.slice(0, 10).map((e: any) => (
                  <div key={e.id} style={{
                    display: 'flex', alignItems: 'center', gap: 8,
                    padding: '6px 0', borderBottom: '1px solid #1a1d29',
                    fontSize: 12, color: '#c4c7d0',
                  }}>
                    <span style={{
                      width: 6, height: 6, borderRadius: '50%',
                      background: '#7c3aed', flexShrink: 0,
                    }} />
                    <span style={{ flex: 1 }}>{e.event_type}</span>
                    <span style={{ fontSize: 10, color: '#7c8299' }}>
                      {e.created_at ? new Date(e.created_at).toLocaleDateString() : ''}
                    </span>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}

function Header() {
  const isMobile = useIsMobile();
  return (
    <div style={{ marginBottom: isMobile ? 16 : 24 }}>
      <h1 style={{ fontSize: isMobile ? 28 : 24, fontWeight: 700, margin: 0, color: '#fff' }}>
        Personal Intelligence
      </h1>
      <p style={{ margin: '4px 0 0', fontSize: isMobile ? 14 : 13, color: '#7c8299' }}>
        Your investigator profile and adaptive learning controls
      </p>
    </div>
  );
}

function SectionTitle({ children }: { children: string }) {
  return (
    <div style={{
      fontSize: 11, fontWeight: 700, color: '#7c8299',
      textTransform: 'uppercase', letterSpacing: 1,
      marginBottom: 12,
    }}>
      {children}
    </div>
  );
}

function StatBox({ label, value }: { label: string; value: string | number }) {
  return (
    <Card padding="md" style={{ textAlign: 'center' }}>
      <div style={{ fontSize: 22, fontWeight: 700, color: '#fff' }}>{value}</div>
      <div style={{ fontSize: 10, fontWeight: 600, color: '#7c8299', textTransform: 'uppercase', letterSpacing: 0.5, marginTop: 2 }}>
        {label}
      </div>
    </Card>
  );
}

function SuccessItem({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ fontSize: 18, fontWeight: 700, color }}>{value}</div>
      <div style={{ fontSize: 10, fontWeight: 600, color: '#7c8299', textTransform: 'uppercase', letterSpacing: 0.5 }}>
        {label}
      </div>
    </div>
  );
}

const btnStyle: React.CSSProperties = {
  padding: '6px 12px', borderRadius: 6, border: '1px solid #2a2e3d',
  background: '#1a1d29', color: '#c4c7d0', fontSize: 12, fontWeight: 600,
  cursor: 'pointer', minHeight: 36,
};
