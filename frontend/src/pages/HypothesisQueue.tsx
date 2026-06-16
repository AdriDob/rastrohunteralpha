import { useState, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useRunHypotheses, useTargets } from '../lib/query';
import { createInvestigation } from '../lib/api';
import type { Hypothesis } from '../types';

const TYPE_COLORS: Record<string, string> = {
  idor: '#f97316',
  auth_bypass: '#ef4444',
  ssrf: '#a855f7',
  xss: '#eab308',
  sqli: '#dc2626',
  graphql_introspection: '#3b82f6',
  privilege_escalation: '#ef4444',
  data_exposure: '#ec4899',
  business_logic: '#14b8a6',
  file_operation: '#f97316',
  ssti: '#8b5cf6',
  web3_rpc_leak: '#6366f1',
  web3_signature_replay: '#6366f1',
  rate_limit_bypass: '#6b7280',
};

const TYPE_LABELS: Record<string, string> = {
  idor: 'IDOR',
  auth_bypass: 'Auth Bypass',
  ssrf: 'SSRF',
  xss: 'XSS',
  sqli: 'SQLi',
  graphql_introspection: 'GraphQL',
  privilege_escalation: 'Priv Esc',
  data_exposure: 'Data Exposure',
  business_logic: 'Business Logic',
  file_operation: 'File Operation',
  ssti: 'SSTI',
  web3_rpc_leak: 'Web3',
  web3_signature_replay: 'Web3',
  rate_limit_bypass: 'Rate Limit',
};

function typeColor(t: string): string {
  return TYPE_COLORS[t.toLowerCase()] ?? '#6b7280';
}
function typeLabel(t: string): string {
  return TYPE_LABELS[t.toLowerCase()] ?? t;
}

function pct(v: number): number {
  return Math.min(Math.max(v * 100, 0), 100);
}

function ScoreBar({ value, color, label }: { value: number; color: string; label: string }) {
  return (
    <div style={{ marginBottom: 6 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#7c8299', marginBottom: 2 }}>
        <span>{label}</span>
        <span>{(value * 100).toFixed(0)}%</span>
      </div>
      <div style={{ height: 4, background: '#0d0f14', borderRadius: 2, overflow: 'hidden' }}>
        <div style={{ width: `${pct(value)}%`, height: '100%', background: color, borderRadius: 2, transition: 'width 0.3s' }} />
      </div>
    </div>
  );
}

function EvidenceTag({ text }: { text: string }) {
  return (
    <span style={{
      display: 'inline-block', fontSize: 10, color: '#c4c7d0',
      background: '#0d0f14', padding: '3px 8px', borderRadius: 4,
      margin: '2px 4px 2px 0',
    }}>
      {text}
    </span>
  );
}

function HypothesisCard({
  h, expanded, onToggle, onPromote,
}: {
  h: Hypothesis; expanded: boolean; onToggle: () => void; onPromote?: () => void;
}) {
  const color = typeColor(h.vulnerability_type);
  const endpointPath = (h.endpoint as any)?.path || '(aggregate)';
  const sources = h.source === 'nuclei' ? `${h.vector}` : h.source;

  return (
    <div style={{
      background: '#1e2230', borderRadius: 8, border: '1px solid #2a2e3d',
      marginBottom: 8, overflow: 'hidden', cursor: 'pointer',
    }}
      onClick={onToggle}
    >
      <div style={{ padding: '14px 18px', display: 'flex', alignItems: 'flex-start', gap: 14 }}>
        <div style={{
          width: 4, height: 48, borderRadius: 2, background: color, flexShrink: 0, marginTop: 2,
        }} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <span style={{
              fontSize: 10, fontWeight: 700, textTransform: 'uppercase',
              letterSpacing: 0.5, color, background: `${color}15`,
              padding: '2px 8px', borderRadius: 4,
            }}>
              {typeLabel(h.vulnerability_type)}
            </span>
            <span style={{ fontSize: 10, color: '#4a4f63' }}>
              {sources} · {endpointPath}
            </span>
            {h.roi_score > 50 && (
              <span style={{
                fontSize: 9, color: '#22c55e', background: '#22c55e15',
                padding: '1px 6px', borderRadius: 3,
              }}>
                PROFITABLE
              </span>
            )}
          </div>
          <div style={{ fontSize: 12, color: '#c4c7d0', lineHeight: 1.5 }}>
            {h.reasoning}
          </div>
          <div style={{ display: 'flex', gap: 16, marginTop: 8 }}>
            {[
              { label: 'Priority', value: h.priority_score.toFixed(1), color },
              { label: 'ROI', value: h.roi_score.toFixed(0), color: h.roi_score > 50 ? '#22c55e' : '#7c8299' },
              { label: 'Confidence', value: (h.confidence * 100).toFixed(0) + '%', color: '#7c8299' },
            ].map((s) => (
              <span key={s.label} style={{ fontSize: 10, color: '#7c8299' }}>
                {s.label}: <strong style={{ color: s.color }}>{s.value}</strong>
              </span>
            ))}
          </div>
        </div>
        <div style={{ width: 120, flexShrink: 0 }}>
          <ScoreBar value={h.likelihood} color="#3b82f6" label="Likelihood" />
          <ScoreBar value={h.impact} color={color} label="Impact" />
          <ScoreBar value={h.exploitability} color="#a855f7" label="Exploitability" />
        </div>
        <span style={{ color: '#4a4f63', fontSize: 11, marginTop: 2 }}>
          {expanded ? '▲' : '▼'}
        </span>
      </div>

      {expanded && (
        <div style={{
          borderTop: '1px solid #2a2e3d', padding: '14px 18px',
          background: '#1a1d29',
        }} onClick={(e) => e.stopPropagation()}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 12 }}>
            <div>
              <SectionTitle>Evidence Used</SectionTitle>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
                {h.evidence.map((e, i) => <EvidenceTag key={i} text={e} />)}
              </div>
            </div>
            <div>
              <SectionTitle>Score Breakdown</SectionTitle>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px 16px', fontSize: 11 }}>
                {Object.entries(h.score?.breakdown ?? {}).filter(([k]) => !k.includes('_breakdown')).map(([k, v]) => (
                  <div key={k} style={{ display: 'flex', justifyContent: 'space-between', color: '#7c8299' }}>
                    <span>{k.replace(/_/g, ' ')}</span>
                    <span style={{ color: '#e2e4e9' }}>{typeof v === 'number' ? v.toFixed(2) : v}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <SectionTitle>Suggested Actions</SectionTitle>
          <ul style={{ margin: '4px 0 12px', paddingLeft: 16, fontSize: 11, color: '#c4c7d0', lineHeight: 1.8 }}>
            {h.suggested_actions.map((a, i) => <li key={i}>{a}</li>)}
          </ul>

          <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
            <ActionBtn color="#7c3aed" onClick={() => {}}>Validate</ActionBtn>
            <ActionBtn color="#4a4f63" onClick={() => {}}>Dismiss</ActionBtn>
            {onPromote ? (
              <ActionBtn color="#2563eb" onClick={onPromote}>Promote to Investigation</ActionBtn>
            ) : (
              <ActionBtn color="#4a4f63" disabled>No target selected</ActionBtn>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ fontSize: 10, fontWeight: 600, color: '#7c8299', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 6 }}>
      {children}
    </div>
  );
}

function ActionBtn({ children, color, disabled, onClick }: {
  children: React.ReactNode; color: string; disabled?: boolean; onClick?: () => void;
}) {
  return (
    <button
      disabled={disabled}
      onClick={onClick}
      style={{
        background: 'transparent', border: `1px solid ${color}`, borderRadius: 6,
        padding: '6px 14px', color: disabled ? '#4a4f63' : color, fontSize: 11,
        fontWeight: 600, cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? 0.5 : 1,
      }}
    >
      {children}
    </button>
  );
}

const ALL_TYPES = ['idor', 'auth_bypass', 'ssrf', 'sqli', 'graphql_introspection', 'privilege_escalation', 'data_exposure', 'business_logic', 'file_operation', 'xss', 'ssti'];

export default function HypothesisQueue() {
  const [searchParams] = useSearchParams();
  const initialTargetId = searchParams.get('targetId');
  const [targetId, setTargetId] = useState<number | null>(
    initialTargetId ? Number(initialTargetId) : null
  );
  const [typeFilter, setTypeFilter] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const navigate = useNavigate();

  const { data: targetsRes } = useTargets();
  const { data: engineOutput, isFetching, error } = useRunHypotheses(targetId);

  const targets = targetsRes?.items ?? [];
  const hypotheses = engineOutput?.attack_queue ?? [];
  const [promoting, setPromoting] = useState<string | null>(null);

  const filtered = useMemo(() => {
    if (!typeFilter) return hypotheses;
    return hypotheses.filter((h) => h.vulnerability_type === typeFilter);
  }, [hypotheses, typeFilter]);

  const toggleExpanded = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handlePromote = async (h: Hypothesis) => {
    const tgtId = h.target_id || targetId;
    if (!tgtId) return;
    setPromoting(h.id);
    try {
      const target = targets.find((t: { id: number }) => t.id === tgtId);
      const invName = `${typeLabel(h.vulnerability_type)} — ${target?.name || `Target #${tgtId}`}`;
      const inv = await createInvestigation({
        target_id: tgtId,
        name: invName,
        notes: `Promoted from hypothesis: ${h.reasoning.slice(0, 200)}`,
        tags: [h.vulnerability_type, 'from_hypothesis'],
      });
      navigate(`/investigation/${inv.id}`);
    } catch {
      // fallback: just navigate to the target
      navigate(`/target/${tgtId}`);
    } finally {
      setPromoting(null);
    }
  };

  const typeCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const h of hypotheses) {
      counts[h.vulnerability_type] = (counts[h.vulnerability_type] || 0) + 1;
    }
    return counts;
  }, [hypotheses]);

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, color: '#fff' }}>Hypothesis Center</h1>
          {targetId && engineOutput && (
            <span style={{
              fontSize: 10, background: '#7c3aed20', color: '#a78bfa',
              padding: '3px 10px', borderRadius: 10, fontWeight: 600,
            }}>
              {engineOutput.total_hypotheses} hypotheses · avg ROI {engineOutput.avg_roi.toFixed(0)}
            </span>
          )}
        </div>
        <p style={{ margin: '4px 0 0', fontSize: 13, color: '#7c8299' }}>
          Attack queue — reasoned vulnerability hypotheses generated from endpoints, nuclei results, and target context
        </p>
      </div>

      <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 20, flexWrap: 'wrap' }}>
        <select
          value={targetId ?? ''}
          onChange={(e) => {
            setTargetId(e.target.value ? Number(e.target.value) : null);
            setExpanded(new Set());
          }}
          style={selectStyle}
        >
          <option value="">Select a target…</option>
          {targets.map((t) => (
            <option key={t.id} value={t.id}>{t.name}</option>
          ))}
        </select>

        {isFetching && (
          <span style={{ color: '#a855f7', fontSize: 13, fontWeight: 600 }}>
            Generating hypotheses…
          </span>
        )}
        {error && (
          <span style={{ color: '#ef4444', fontSize: 13 }}>{(error as Error).message}</span>
        )}
      </div>

      {engineOutput && (
        <>
          <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
            <FilterPill
              label="All"
              active={typeFilter === null}
              count={hypotheses.length}
              onClick={() => setTypeFilter(null)}
            />
            {ALL_TYPES.filter((t) => typeCounts[t]).map((t) => (
              <FilterPill
                key={t}
                label={typeLabel(t)}
                active={typeFilter === t}
                count={typeCounts[t] ?? 0}
                color={typeColor(t)}
                onClick={() => setTypeFilter(t)}
              />
            ))}
          </div>

          {engineOutput.top_priority && !typeFilter && (
            <div
              onClick={() => toggleExpanded(engineOutput.top_priority!.id)}
              style={{
                background: 'linear-gradient(135deg, #1e1b4b, #312e81)',
                border: '1px solid #4c1d95', borderRadius: 8,
                padding: '14px 18px', marginBottom: 16, cursor: 'pointer',
              }}
            >
              <div style={{ fontSize: 10, fontWeight: 700, color: '#a78bfa', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4 }}>
                ★ Top Priority
              </div>
              <div style={{ fontSize: 13, color: '#e2e4e9', lineHeight: 1.5 }}>
                [{typeLabel(engineOutput.top_priority.vulnerability_type)}] {engineOutput.top_priority.reasoning}
              </div>
              <div style={{ display: 'flex', gap: 12, marginTop: 6 }}>
                <ScoreBar value={engineOutput.top_priority.likelihood} color="#3b82f6" label="L" />
                <ScoreBar value={engineOutput.top_priority.impact} color={typeColor(engineOutput.top_priority.vulnerability_type)} label="I" />
                <ScoreBar value={engineOutput.top_priority.exploitability} color="#a855f7" label="E" />
              </div>
            </div>
          )}

          {filtered.length === 0 && (
            <div style={{ textAlign: 'center', padding: 40, color: '#7c8299', fontSize: 13 }}>
              {hypotheses.length > 0
                ? 'No hypotheses match the selected filter.'
                : 'Select a target and the engine will generate hypotheses.'}
            </div>
          )}

          {filtered.map((h) => (
            <HypothesisCard
              key={h.id}
              h={h}
              expanded={expanded.has(h.id)}
              onToggle={() => toggleExpanded(h.id)}
              onPromote={promoting === h.id ? undefined : () => handlePromote(h)}
            />
          ))}
        </>
      )}

      {!engineOutput && !isFetching && targetId === null && (
        <div style={{
          textAlign: 'center', padding: 60, color: '#7c8299',
          background: '#1a1d29', borderRadius: 8, border: '1px solid #2a2e3d',
        }}>
          <div style={{ fontSize: 32, marginBottom: 12 }}>⟐</div>
          <p style={{ fontSize: 14, margin: 0 }}>
            Select a target above to generate vulnerability hypotheses
          </p>
          <p style={{ fontSize: 12, margin: '8px 0 0', color: '#4a4f63' }}>
            The engine analyzes endpoints, nuclei results, and auth context to produce reasoned attack vectors
          </p>
        </div>
      )}
    </div>
  );
}

function FilterPill({ label, active, count, color, onClick }: {
  label: string; active: boolean; count: number; color?: string; onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        background: active ? '#7c3aed' : 'transparent',
        border: `1px solid ${active ? '#7c3aed' : '#2a2e3d'}`,
        borderRadius: 14, padding: '4px 14px', cursor: 'pointer',
        color: active ? '#fff' : color ?? '#7c8299', fontSize: 11, fontWeight: 600,
        display: 'flex', alignItems: 'center', gap: 6,
      }}
    >
      <span>{label}</span>
      <span style={{ fontSize: 10, opacity: 0.7 }}>{count}</span>
    </button>
  );
}

const selectStyle: React.CSSProperties = {
  background: '#1a1d29', border: '1px solid #2a2e3d', borderRadius: 6,
  padding: '8px 14px', color: '#e2e4e9', fontSize: 13, outline: 'none', minWidth: 220,
};
