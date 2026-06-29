interface KPICardProps {
  label: string;
  value: string | number;
  icon?: string;
  accent?: string;
}

export default function KPICard({ label, value, icon = '◈', accent = 'rgba(59,130,246,0.12)' }: KPICardProps) {
  return (
    <div style={{
      background: '#161B22', borderRadius: 14, border: '1px solid #212838',
      padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: 8,
      boxShadow: '0 1px 2px rgba(0,0,0,0.3)',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <div style={{
            fontSize: 11, color: '#A0A8B3', textTransform: 'uppercase', letterSpacing: 0.5, fontWeight: 600,
          }}>
            {label}
          </div>
          <div style={{
            fontSize: 26, fontWeight: 700, color: '#F8FAFC', lineHeight: 1.1,
          }}>
            {value}
          </div>
        </div>
        <div style={{
          width: 36, height: 36, borderRadius: 10, display: 'flex', alignItems: 'center',
          justifyContent: 'center', fontSize: 16, background: accent, flexShrink: 0,
        }}>
          {icon}
        </div>
      </div>
    </div>
  );
}
