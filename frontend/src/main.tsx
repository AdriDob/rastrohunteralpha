import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

// PrimeReact theme — must be imported before app CSS
import 'primereact/resources/themes/lara-dark-blue/theme.css'
import 'primeicons/primeicons.css'

import './index.css'
import App from './App.tsx'
import { RastroDesignSystemProvider } from './design-system/provider'

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/service-worker.js').catch((err) => {
      console.warn('[SW] Service worker registration failed (non-fatal):', err);
    });
  }, { once: true });
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <RastroDesignSystemProvider>
      <App />
    </RastroDesignSystemProvider>
  </StrictMode>,
)
