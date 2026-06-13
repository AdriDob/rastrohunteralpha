import { useState } from 'react';

interface TourStep {
  title: string;
  description: string;
  /** CSS selector for the element to highlight */
  target: string;
  /** Position of the tooltip relative to target */
  position: 'bottom' | 'right' | 'left';
}

const STEPS: TourStep[] = [
  {
    title: 'Sidebar Navigation',
    description: 'Access all sections from here: Targets, Endpoints, Findings, and more.',
    target: '[class*="sidebar"]',
    position: 'right',
  },
  {
    title: 'Command Palette',
    description: 'Press Ctrl+K (or Cmd+K) to quickly search and navigate anywhere.',
    target: '[class*="command"]',
    position: 'bottom',
  },
  {
    title: 'Mission Control',
    description: 'This is your dashboard. Key metrics, quick actions, and top targets at a glance.',
    target: '[class*="mission"]',
    position: 'bottom',
  },
];

interface TourOverlayProps {
  onComplete: () => void;
}

export default function TourOverlay({ onComplete }: TourOverlayProps) {
  const [step, setStep] = useState(0);

  const current = STEPS[step];

  const handleNext = () => {
    if (step < STEPS.length - 1) {
      setStep(s => s + 1);
    } else {
      localStorage.setItem('rastro-tour-complete', 'true');
      onComplete();
    }
  };

  const handleSkip = () => {
    localStorage.setItem('rastro-tour-complete', 'true');
    onComplete();
  };

  return (
    <>
      {/* Overlay backdrop */}
      <div style={{
        position: 'fixed', inset: 0, zIndex: 9997,
        background: 'rgba(19, 21, 29, 0.7)',
      }} />

      {/* Tooltip */}
      <div style={{
        position: 'fixed', zIndex: 9998,
        bottom: 40, left: '50%', transform: 'translateX(-50%)',
        maxWidth: 380, width: '90%',
        padding: '20px 24px', borderRadius: 12,
        background: '#1a1d2e', border: '1px solid #2a2e3d',
      }}>
        <div style={{ fontSize: 11, color: '#7c3aed', fontWeight: 600, marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Tour {step + 1} of {STEPS.length}
        </div>
        <h3 style={{ fontSize: 15, fontWeight: 600, color: '#e0e0e0', margin: '4px 0 6px' }}>
          {current.title}
        </h3>
        <p style={{ fontSize: 13, color: '#7c8299', margin: 0, lineHeight: 1.5 }}>
          {current.description}
        </p>

        <div style={{ display: 'flex', gap: 8, justifyContent: 'center', margin: '16px 0' }}>
          {STEPS.map((_, i) => (
            <div key={i} style={{
              width: 6, height: 6, borderRadius: '50%',
              background: i === step ? '#7c3aed' : '#2a2e3d',
              transition: 'background 0.3s',
            }} />
          ))}
        </div>

        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={handleSkip}
            style={{
              flex: 1, padding: '8px', borderRadius: 6, border: '1px solid #2a2e3d',
              background: 'transparent', color: '#7c8299', fontSize: 13, cursor: 'pointer',
            }}
          >
            Skip Tour
          </button>
          <button
            onClick={handleNext}
            style={{
              flex: 2, padding: '8px', borderRadius: 6, border: 'none',
              background: '#7c3aed', color: '#fff', fontSize: 13, fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            {step < STEPS.length - 1 ? 'Next' : 'Finish'}
          </button>
        </div>
      </div>
    </>
  );
}
