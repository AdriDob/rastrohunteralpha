import { type ReactNode, useCallback } from 'react';

interface CardProps {
  children: ReactNode;
  onClick?: () => void;
  accent?: 'primary' | 'secondary' | 'risk' | 'none';
  padding?: 'sm' | 'md' | 'lg';
  style?: React.CSSProperties;
}

const accentColors = {
  primary: { border: '#7c3aed', glow: 'rgba(124,58,237,0.12)' },
  secondary: { border: '#2a2e3d', glow: 'transparent' },
  risk: { border: '#ef4444', glow: 'rgba(239,68,68,0.08)' },
  none: { border: '#2a2e3d', glow: 'transparent' },
};

const paddings = { sm: '10px 14px', md: '14px 18px', lg: '20px 22px' };

export default function Card({
  children, onClick, accent = 'secondary',
  padding = 'md', style,
}: CardProps) {
  const cc = accentColors[accent];
  const pad = paddings[padding];
  const isClickable = onClick !== undefined;

  const handleMouseEnter = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!isClickable) return;
    e.currentTarget.style.borderColor = '#3b3f52';
    e.currentTarget.style.background = '#1e2230';
  }, [isClickable]);

  const handleMouseLeave = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    e.currentTarget.style.borderColor = cc.border;
    e.currentTarget.style.background = '#1a1d29';
  }, [cc.border]);

  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!isClickable) return;
    e.currentTarget.style.transform = 'scale(0.98)';
  }, [isClickable]);

  const handleMouseUp = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!isClickable) return;
    e.currentTarget.style.transform = 'scale(1)';
  }, [isClickable]);

  return (
    <div
      onClick={onClick}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onMouseDown={handleMouseDown}
      onMouseUp={handleMouseUp}
      role={isClickable ? 'button' : undefined}
      tabIndex={isClickable ? 0 : undefined}
      onKeyDown={isClickable ? (e) => { if (e.key === 'Enter') onClick?.(); } : undefined}
      style={{
        background: '#1a1d29',
        borderRadius: 10,
        border: `1px solid ${cc.border}`,
        padding: pad,
        cursor: isClickable ? 'pointer' : undefined,
        transition: 'all 0.15s ease',
        boxShadow: cc.glow !== 'transparent' ? `0 0 16px ${cc.glow}` : undefined,
        ...style,
      }}
    >
      {children}
    </div>
  );
}
