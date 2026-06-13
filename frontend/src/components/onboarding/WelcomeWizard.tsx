import { useState } from 'react';

const STEPS = [
  {
    title: 'Welcome to Rastro',
    description: 'Your investigation OS for bug bounty hunting. Rastro helps you discover, analyze, and validate attack surface across your targets.',
    icon: 'R',
  },
  {
    title: 'Add Your First Target',
    description: 'Start by adding a target domain. Rastro will scan it for endpoints, find vulnerabilities, and prioritize the best opportunities.',
    icon: '🎯',
  },
  {
    title: 'AI-Powered Analysis',
    description: 'Rastro\'s AI copilot analyzes findings, generates hypotheses, and provides actionable recommendations based on bounty potential.',
    icon: '🤖',
  },
];

interface WelcomeWizardProps {
  onComplete: () => void;
}

export default function WelcomeWizard({ onComplete }: WelcomeWizardProps) {
  const [step, setStep] = useState(0);
  const current = STEPS[step];

  const handleNext = () => {
    if (step < STEPS.length - 1) {
      setStep(s => s + 1);
    } else {
      localStorage.setItem('rastro-onboarding-complete', 'true');
      onComplete();
    }
  };

  const handleSkip = () => {
    localStorage.setItem('rastro-onboarding-complete', 'true');
    onComplete();
  };

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 9998,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: '#13151d',
    }}>
      <div style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        padding: '56px 48px', borderRadius: 16,
        background: '#1a1d2e', border: '1px solid #2a2e3d',
        maxWidth: 460, width: '90%', textAlign: 'center',
      }}>
        {/* Icon/Logo */}
        <div style={{
          width: 72, height: 72, borderRadius: 18,
          background: 'linear-gradient(135deg, #7c3aed, #a855f7)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 32, fontWeight: 800, color: '#fff', marginBottom: 24,
        }}>
          {current.icon}
        </div>

        {/* Title */}
        <h1 style={{ fontSize: 22, fontWeight: 700, color: '#e0e0e0', margin: 0 }}>
          {current.title}
        </h1>

        {/* Description */}
        <p style={{ fontSize: 14, color: '#7c8299', lineHeight: 1.6, margin: '16px 0 32px' }}>
          {current.description}
        </p>

        {/* Step dots */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 32 }}>
          {STEPS.map((_, i) => (
            <div key={i} style={{
              width: 8, height: 8, borderRadius: '50%',
              background: i === step ? '#7c3aed' : '#2a2e3d',
              transition: 'background 0.3s',
            }} />
          ))}
        </div>

        {/* Buttons */}
        <div style={{ display: 'flex', gap: 12, width: '100%' }}>
          <button
            onClick={handleSkip}
            style={{
              flex: 1, padding: '12px', borderRadius: 8, border: '1px solid #2a2e3d',
              background: 'transparent', color: '#7c8299', fontSize: 14, fontWeight: 500,
              cursor: 'pointer',
            }}
          >
            Skip
          </button>
          <button
            onClick={handleNext}
            style={{
              flex: 2, padding: '12px', borderRadius: 8, border: 'none',
              background: '#7c3aed', color: '#fff', fontSize: 14, fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            {step < STEPS.length - 1 ? 'Next' : 'Start Exploring'}
          </button>
        </div>
      </div>
    </div>
  );
}
