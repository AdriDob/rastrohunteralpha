import { useState, useCallback } from 'react';
import { useScreenshots } from '../lib/query';
import Panel from '../components/ui/Panel';
import Badge from '../components/ui/Badge';
import { SkeletonPanel } from '../components/ui/Skeleton';
import type { ScreenshotSpec } from '../types';

const blockColors: Record<string, string> = {
  request: '#3b82f6',
  response: '#22c55e',
  diff: '#f97316',
  graph: '#a855f7',
  roi: '#eab308',
  auth: '#ef4444',
  state_change: '#8b5cf6',
  contract_call: '#06b6d4',
};

const blockIcons: Record<string, string> = {
  request: '→',
  response: '←',
  diff: 'Δ',
  graph: '◉',
  roi: '$',
  auth: '🔒',
  state_change: '⚡',
  contract_call: '◎',
};

function SpecThumbnail({ spec, onClick }: { spec: ScreenshotSpec; onClick: () => void }) {
  const severityColor = { critical: '#ef4444', high: '#f97316', medium: '#eab308', low: '#3b82f6', info: '#6b7280' }[spec.severity] || '#6b7280';

  return (
    <div
      onClick={onClick}
      onKeyDown={(e) => e.key === 'Enter' && onClick()}
      tabIndex={0}
      role="button"
      style={{
        background: '#1e2230', borderRadius: 8, border: '1px solid #2a2e3d',
        padding: 14, cursor: 'pointer', transition: 'all 0.15s',
        display: 'flex', flexDirection: 'column', gap: 8,
      }}
      onMouseEnter={(e) => { e.currentTarget.style.borderColor = severityColor; e.currentTarget.style.background = '#222639'; }}
      onMouseLeave={(e) => { e.currentTarget.style.borderColor = '#2a2e3d'; e.currentTarget.style.background = '#1e2230'; }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <Badge text={spec.severity} variant="severity" />
        <Badge text={spec.vulnerability_type} color="#8b5cf6" />
      </div>
      <div style={{ fontSize: 13, fontWeight: 600, color: '#e2e4e9', lineHeight: 1.4 }}>{spec.title}</div>
      <div style={{ fontSize: 11, color: '#7c8299' }}>{spec.endpoint}</div>
      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
        {spec.visual_blocks.slice(0, 4).map((b, i) => (
          <span key={i} style={{
            fontSize: 9, padding: '2px 6px', borderRadius: 4,
            background: `${blockColors[b.type] || '#6b7280'}20`,
            color: blockColors[b.type] || '#6b7280',
          }}>
            {blockIcons[b.type] || '▪'} {b.type}
          </span>
        ))}
      </div>
      {spec.roi_score > 0 && (
        <div style={{ fontSize: 12, color: '#22c55e', fontWeight: 600 }}>
          ROI: {spec.roi_score.toFixed(1)}
        </div>
      )}
    </div>
  );
}

function SpecDetail({ spec, onClose }: { spec: ScreenshotSpec; onClose: () => void }) {
  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 100,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'rgba(0,0,0,0.7)', padding: 40,
    }}
      onClick={onClose}
      onKeyDown={(e) => e.key === 'Escape' && onClose()}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          maxWidth: 800, width: '100%', maxHeight: '90vh', overflow: 'auto',
          background: '#1a1d29', borderRadius: 12, border: '1px solid #2a2e3d',
          padding: 28,
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
          <div>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: '#fff', margin: 0 }}>{spec.title}</h2>
            <div style={{ fontSize: 12, color: '#7c8299', marginTop: 4 }}>{spec.target} · {spec.endpoint}</div>
          </div>
          <button onClick={onClose} style={{
            background: 'none', border: 'none', color: '#7c8299', fontSize: 20, cursor: 'pointer',
          }}>✕</button>
        </div>

        <div style={{ display: 'flex', gap: 12, marginBottom: 20 }}>
          <Badge text={spec.severity} variant="severity" size="md" />
          <Badge text={spec.vulnerability_type} color="#8b5cf6" size="md" />
          {spec.confidence > 0 && <Badge text={`Conf: ${(spec.confidence * 100).toFixed(0)}%`} color="#22c55e" size="md" />}
        </div>

        {spec.attack_path_summary && (
          <div style={{ padding: '10px 14px', borderRadius: 6, background: '#1e2230', border: '1px solid #2a2e3d', marginBottom: 16 }}>
            <div style={{ fontSize: 11, color: '#7c8299', marginBottom: 4, fontWeight: 600 }}>ATTACK PATH</div>
            <div style={{ fontSize: 13, color: '#c4c7d0', lineHeight: 1.5 }}>{spec.attack_path_summary}</div>
          </div>
        )}

        {spec.before_state && spec.after_state && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
            <div style={{ padding: 10, borderRadius: 6, background: '#1e2230', border: '1px solid #2a2e3d' }}>
              <div style={{ fontSize: 10, color: '#7c8299', fontWeight: 600, marginBottom: 4 }}>BEFORE</div>
              <div style={{ fontSize: 12, color: '#c4c7d0', fontFamily: 'monospace' }}>{spec.before_state}</div>
            </div>
            <div style={{ padding: 10, borderRadius: 6, background: '#1e2230', border: '1px solid #f9731630' }}>
              <div style={{ fontSize: 10, color: '#f97316', fontWeight: 600, marginBottom: 4 }}>AFTER</div>
              <div style={{ fontSize: 12, color: '#c4c7d0', fontFamily: 'monospace' }}>{spec.after_state}</div>
            </div>
          </div>
        )}

        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 11, color: '#7c8299', fontWeight: 600, marginBottom: 8 }}>VISUAL BLOCKS</div>
          {spec.visual_blocks.map((b, i) => (
            <div key={i} style={{
              padding: '10px 14px', borderRadius: 6, marginBottom: 6,
              background: '#1e2230', borderLeft: `3px solid ${blockColors[b.type] || '#6b7280'}`,
            }}>
              <div style={{ fontSize: 10, color: blockColors[b.type] || '#6b7280', fontWeight: 600, marginBottom: 4, textTransform: 'uppercase' }}>
                {blockIcons[b.type] || '▪'} {b.type}
                {b.highlight_level !== 'low' && <span style={{ marginLeft: 6 }}>({b.highlight_level})</span>}
              </div>
              <div style={{ fontSize: 12, color: '#c4c7d0', fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>{b.content}</div>
            </div>
          ))}
        </div>

        {spec.annotations.length > 0 && (
          <div>
            <div style={{ fontSize: 11, color: '#7c8299', fontWeight: 600, marginBottom: 8 }}>ANNOTATIONS</div>
            {spec.annotations.map((a, i) => (
              <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'flex-start', marginBottom: 6 }}>
                <Badge text={a.category} color={
                  a.severity === 'critical' ? '#ef4444' : a.severity === 'high' ? '#f97316' : '#eab308'
                } />
                <span style={{ fontSize: 12, color: '#c4c7d0' }}>{a.detail}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function ScreenshotCenter() {
  const { data, isLoading } = useScreenshots();
  const [selectedSpec, setSelectedSpec] = useState<ScreenshotSpec | null>(null);

  const handleClose = useCallback(() => setSelectedSpec(null), []);

  if (isLoading) {
    return (
      <div>
        <div style={{ marginBottom: 24 }}>
          <div style={{ fontSize: 22, fontWeight: 700, color: '#fff' }}>Screenshot Center</div>
          <div style={{ fontSize: 13, color: '#7c8299' }}>Loading visual evidence...</div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
          {Array.from({ length: 6 }).map((_, i) => <SkeletonPanel key={i} />)}
        </div>
      </div>
    );
  }

  const specs = data?.specs ?? [];

  return (
    <div style={{ maxWidth: 1400 }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, color: '#fff' }}>Screenshot Center</h1>
        <p style={{ margin: '4px 0 0', fontSize: 13, color: '#7c8299' }}>
          {data?.summary || (specs.length > 0 ? `${specs.length} visual evidence items` : 'No visual evidence available')}
        </p>
      </div>

      {data?.key_risks && data.key_risks.length > 0 && (
        <div style={{ display: 'flex', gap: 6, marginBottom: 16, flexWrap: 'wrap' }}>
          {data.key_risks.map((risk, i) => (
            <Badge key={i} text={risk} variant="severity" size="md" />
          ))}
        </div>
      )}

      {specs.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 60, color: '#7c8299', background: '#1a1d29', borderRadius: 10, border: '1px solid #2a2e3d' }}>
          <div style={{ fontSize: 40, marginBottom: 12 }}>🖼️</div>
          <div style={{ fontSize: 16, fontWeight: 600, color: '#e2e4e9' }}>No Screenshots Yet</div>
          <div style={{ fontSize: 13, marginTop: 4 }}>Evidence and findings will appear here as visual cards</div>
        </div>
      ) : (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12, marginBottom: 16 }}>
            {specs.map((spec, i) => (
              <SpecThumbnail key={i} spec={spec} onClick={() => setSelectedSpec(spec)} />
            ))}
          </div>

          {data?.roi_highlights && data.roi_highlights.length > 0 && (
            <Panel title="💰 ROI Highlights" accent="#22c55e" empty={false}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {data.roi_highlights.map((h, i) => (
                  <div key={i} style={{ fontSize: 12, color: '#c4c7d0', padding: '4px 0' }}>• {h}</div>
                ))}
              </div>
            </Panel>
          )}
        </>
      )}

      {selectedSpec && <SpecDetail spec={selectedSpec} onClose={handleClose} />}
    </div>
  );
}
