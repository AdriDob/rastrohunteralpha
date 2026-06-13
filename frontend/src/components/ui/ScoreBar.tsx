interface ScoreBarProps {
  value: number;
  max?: number;
  label?: string;
  color?: string;
  height?: number;
  showLabel?: boolean;
}

function getColor(ratio: number): string {
  if (ratio >= 0.8) return '#22c55e';
  if (ratio >= 0.6) return '#eab308';
  if (ratio >= 0.4) return '#f97316';
  return '#ef4444';
}

export default function ScoreBar({
  value, max = 1, label, color, height = 8, showLabel = true,
}: ScoreBarProps) {
  const ratio = Math.min(value / max, 1);
  const barColor = color || getColor(ratio);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {(label || showLabel) && (
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#7c8299' }}>
          <span>{label || ''}</span>
          <span style={{ fontWeight: 600, color: barColor }}>
            {typeof value === 'number' ? value.toFixed(2) : value}
          </span>
        </div>
      )}
      <div style={{
        width: '100%', height, borderRadius: 4,
        background: '#2a2e3d', overflow: 'hidden',
      }}>
        <div style={{
          width: `${ratio * 100}%`, height: '100%',
          borderRadius: 4,
          background: barColor,
          transition: 'width 0.5s ease',
        }} />
      </div>
    </div>
  );
}
