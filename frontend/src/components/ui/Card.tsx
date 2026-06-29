import { type ReactNode, useCallback } from 'react';

interface CardProps {
  children: ReactNode;
  onClick?: () => void;
  accent?: string;
  padding?: 'sm' | 'md' | 'lg';
  style?: React.CSSProperties;
}

const paddings = { sm: '12px 16px', md: '16px 20px', lg: '20px 24px' };

export default function Card({
  children, onClick, padding = 'md', style,
}: CardProps) {
  const isClickable = onClick !== undefined;

  const handleMouseEnter = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!isClickable) return;
    e.currentTarget.style.borderColor = '#2D3548';
    e.currentTarget.style.background = '#1F252E';
  }, [isClickable]);

  const handleMouseLeave = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    e.currentTarget.style.borderColor = '#212838';
    e.currentTarget.style.background = '#161B22';
  }, []);

  return (
    <div
      onClick={onClick}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      role={isClickable ? 'button' : undefined}
      tabIndex={isClickable ? 0 : undefined}
      onKeyDown={isClickable ? (e) => { if (e.key === 'Enter') onClick?.(); } : undefined}
      style={{
        background: '#161B22',
        borderRadius: 14,
        border: '1px solid #212838',
        padding: paddings[padding],
        cursor: isClickable ? 'pointer' : undefined,
        transition: 'all 0.15s ease',
        boxShadow: '0 1px 2px rgba(0,0,0,0.3)',
        ...style,
      }}
    >
      {children}
    </div>
  );
}
