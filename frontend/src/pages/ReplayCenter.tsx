import { useState, useCallback } from 'react';
import { useReplayTargets, useReplay } from '../lib/query';
import Panel from '../components/ui/Panel';
import Badge from '../components/ui/Badge';
import { SkeletonPanel } from '../components/ui/Skeleton';
import type { ReplayTarget, ReplayFrame } from '../types';

const stageConfig: Record<string, { label: string; color: string; icon: string }> = {
  recon: { label: 'Recon', color: '#8b5cf6', icon: '🔍' },
  endpoint_discovered: { label: 'Endpoints', color: '#3b82f6', icon: '🔀' },
  hot_path_detected: { label: 'Hot Paths', color: '#f97316', icon: '⚡' },
  evidence_generated: { label: 'Evidence', color: '#22c55e', icon: '📋' },
  verdict_assigned: { label: 'Verdicts', color: '#eab308', icon: '⚖️' },
  report_generated: { label: 'Reports', color: '#ef4444', icon: '📄' },
  finding_created: { label: 'Findings', color: '#a855f7', icon: '🎯' },
  ai_explanation: { label: 'AI Summary', color: '#06b6d4', icon: '🤖' },
  quick_win_created: { label: 'Quick Wins', color: '#22c55e', icon: '💨' },
  historical_memory_updated: { label: 'Memory', color: '#6b7280', icon: '🧠' },
};

function getStageConfig(stage: string) {
  return stageConfig[stage] || { label: stage, color: '#6b7280', icon: '▪' };
}

const stages = ['recon', 'endpoint_discovered', 'hot_path_detected', 'evidence_generated', 'verdict_assigned', 'finding_created', 'report_generated'];

export default function ReplayCenter() {
  const { data: targetsData, isLoading: targetsLoading } = useReplayTargets();
  const [selectedTargetId, setSelectedTargetId] = useState<number | null>(null);
  const { data: replay, isLoading: replayLoading } = useReplay(selectedTargetId);

  const targets = targetsData?.targets ?? [];

  const handleSelectTarget = useCallback((id: number) => {
    setSelectedTargetId(id);
  }, []);

  const frames = replay?.timeline ?? [];
  const frameStages = new Set(frames.map((f) => f.stage));
  const timelineFrames = frames.sort((a, b) => a.timestamp.localeCompare(b.timestamp));

  return (
    <div style={{ maxWidth: 1400 }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, color: '#fff' }}>Replay Center</h1>
        <p style={{ margin: '4px 0 0', fontSize: 13, color: '#7c8299' }}>Investigation timeline — navigate through every stage</p>
      </div>

      {targetsLoading ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
          {Array.from({ length: 4 }).map((_, i) => <SkeletonPanel key={i} />)}
        </div>
      ) : targets.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 60, color: '#7c8299', background: '#1a1d29', borderRadius: 10, border: '1px solid #2a2e3d' }}>
          <div style={{ fontSize: 40, marginBottom: 12 }}>🎬</div>
          <div style={{ fontSize: 16, fontWeight: 600, color: '#e2e4e9' }}>No Replays Available</div>
          <div style={{ fontSize: 13, marginTop: 4 }}>Scans and findings will generate replay data</div>
        </div>
      ) : (
        <>
          {/* Target selector */}
          <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap' }}>
            {targets.map((t: ReplayTarget) => (
              <div
                key={t.id}
                onClick={() => handleSelectTarget(t.id)}
                onKeyDown={(e) => e.key === 'Enter' && handleSelectTarget(t.id)}
                tabIndex={0}
                role="button"
                style={{
                  padding: '10px 16px', borderRadius: 8, cursor: 'pointer',
                  background: selectedTargetId === t.id ? '#7c3aed' : '#1e2230',
                  border: `1px solid ${selectedTargetId === t.id ? '#7c3aed' : '#2a2e3d'}`,
                  transition: 'all 0.15s',
                }}
              >
                <div style={{ fontSize: 13, fontWeight: 600, color: selectedTargetId === t.id ? '#fff' : '#e2e4e9' }}>{t.name}</div>
                <div style={{ fontSize: 10, color: selectedTargetId === t.id ? '#c4c7d0' : '#7c8299', marginTop: 2 }}>
                  {t.domain || 'No domain'}
                </div>
              </div>
            ))}
          </div>

          {/* Stage navigation */}
          {replay && (
            <div style={{ display: 'flex', gap: 6, marginBottom: 20, overflowX: 'auto', padding: '4px 0' }}>
              {stages.map((stage) => {
                const cfg = getStageConfig(stage);
                const hasData = frameStages.has(stage);
                return (
                  <div
                    key={stage}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 6,
                      padding: '8px 14px', borderRadius: 8,
                      background: hasData ? `${cfg.color}15` : '#1e2230',
                      border: `1px solid ${hasData ? `${cfg.color}40` : '#2a2e3d'}`,
                      opacity: hasData ? 1 : 0.4,
                      cursor: hasData ? 'pointer' : 'default',
                      transition: 'all 0.15s',
                    }}
                    onClick={() => {
                      const el = document.getElementById(`stage-${stage}`);
                      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }}
                  >
                    <span>{cfg.icon}</span>
                    <span style={{ fontSize: 11, fontWeight: 600, color: hasData ? cfg.color : '#7c8299' }}>
                      {cfg.label}
                    </span>
                  </div>
                );
              })}
            </div>
          )}

          {replayLoading ? (
            <SkeletonPanel />
          ) : replay ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {/* Summary stats */}
              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 8 }}>
                <Badge text={`${replay.endpoints.length} endpoints`} color="#3b82f6" size="md" />
                <Badge text={`${replay.findings.length} findings`} color="#a855f7" size="md" />
                <Badge text={`${replay.verdicts.length} verdicts`} color="#eab308" size="md" />
                <Badge text={`${replay.evidence.length} evidence`} color="#22c55e" size="md" />
                <Badge text={`${replay.total_frames} timeline frames`} color="#8b5cf6" size="md" />
              </div>

              {/* Timeline ordered by stage */}
              {stages.map((stage) => {
                const cfg = getStageConfig(stage);
                const stageFrames = timelineFrames.filter((f) => f.stage === stage);
                if (stageFrames.length === 0) return null;

                return (
                  <div key={stage} id={`stage-${stage}`}>
                    <Panel
                      title={`${cfg.icon} ${cfg.label}`}
                      subtitle={`${stageFrames.length} event${stageFrames.length !== 1 ? 's' : ''}`}
                      accent={cfg.color}
                    >
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                        {stageFrames.map((frame: ReplayFrame, i: number) => (
                          <div key={i} style={{
                            padding: '8px 12px', borderRadius: 6,
                            background: '#1e2230', border: '1px solid #2a2e3d',
                          }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <div style={{ fontSize: 12, color: '#c4c7d0' }}>{frame.summary || frame.stage}</div>
                              <span style={{ fontSize: 10, color: '#7c8299' }}>
                                {frame.timestamp ? new Date(frame.timestamp).toLocaleString() : ''}
                              </span>
                            </div>
                            {Object.keys(frame.data).length > 0 && (
                              <div style={{ marginTop: 4, fontSize: 10, color: '#7c8299', fontFamily: 'monospace' }}>
                                {JSON.stringify(frame.data).slice(0, 120)}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </Panel>
                  </div>
                );
              })}
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: 60, color: '#7c8299' }}>
              Select a target above to view replay
            </div>
          )}
        </>
      )}
    </div>
  );
}
