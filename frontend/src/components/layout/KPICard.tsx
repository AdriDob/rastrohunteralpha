interface KPICardProps {
  label: string;
  value: string | number;
  icon?: string;
  accent?: string;
}

const cardStyle: React.CSSProperties = {
  background: '#1e2230', borderRadius: 8, border: '1px solid #2a2e3d',
  padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: 6,
};

const valueStyle: React.CSSProperties = {
  fontSize: 28, fontWeight: 700, color: '#fff', lineHeight: 1.1,
};

const labelStyle: React.CSSProperties = {
  fontSize: 11, color: '#7c8299', textTransform: 'uppercase', letterSpacing: 0.5, fontWeight: 600,
};

const iconStyle = (accent: string): React.CSSProperties => ({
  width: 36, height: 36, borderRadius: 8, display: 'flex', alignItems: 'center',
  justifyContent: 'center', fontSize: 16, background: accent,
});

export default function KPICard({ label, value, icon = '◈', accent = 'rgba(124,58,237,0.12)' }: KPICardProps) {
  return (
    <div style={cardStyle}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={labelStyle}>{label}</div>
          <div style={valueStyle}>{value}</div>
        </div>
        <div style={iconStyle(accent)}>{icon}</div>
      </div>
    </div>
  );
}
