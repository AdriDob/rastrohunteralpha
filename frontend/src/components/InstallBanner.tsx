import { useState, useEffect } from 'react';

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

export default function InstallBanner() {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    const handler = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
    };
    window.addEventListener('beforeinstallprompt', handler);
    return () => window.removeEventListener('beforeinstallprompt', handler);
  }, []);

  const isStandalone = matchMedia('(display-mode: standalone)').matches ||
    (window.navigator as any).standalone === true;

  if (isStandalone || !deferredPrompt || dismissed) return null;

  const handleInstall = async () => {
    if (!deferredPrompt) return;
    try {
      deferredPrompt.prompt();
      const result = await deferredPrompt.userChoice;
      if (result.outcome === 'accepted') {
        setDeferredPrompt(null);
      }
    } catch {
      // install prompt failed
    }
  };

  return (
    <div style={{
      position: 'fixed', bottom: 16, left: 16, right: 16, zIndex: 9999,
      background: '#1e2230', border: '1px solid #2a2e3d', borderRadius: 12,
      padding: '14px 16px', boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
      display: 'flex', alignItems: 'center', gap: 12, maxWidth: 400, margin: '0 auto',
    }}>
      <div style={{ fontSize: 28 }}>📡</div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 700, fontSize: 14, color: '#fff' }}>Install Rastro</div>
        <div style={{ fontSize: 12, color: '#7c8299' }}>Get real-time opportunities even offline</div>
      </div>
      <div style={{ display: 'flex', gap: 6 }}>
        <button
          onClick={() => setDismissed(true)}
          style={{
            background: 'transparent', border: 'none', color: '#7c8299',
            cursor: 'pointer', fontSize: 12, padding: '6px 10px',
          }}
        >
          Later
        </button>
        <button
          onClick={handleInstall}
          style={{
            background: '#7c3aed', border: 'none', borderRadius: 8,
            color: '#fff', cursor: 'pointer', fontSize: 13, fontWeight: 600,
            padding: '8px 16px',
          }}
        >
          Install
        </button>
      </div>
    </div>
  );
}
