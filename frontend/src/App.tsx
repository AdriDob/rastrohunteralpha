import { useState, useEffect, useCallback, useMemo, lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, useNavigate, useSearchParams, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { setAuthToken, setOnAuthRedirect } from './lib/api';
import { useUI, useLicense } from './lib/store';
import { StateContinuityProvider } from './lib/stateContinuity';
import { GlobalErrorBoundaryUI } from './components/ui/GlobalErrorBoundaryUI';
import Layout from './components/layout/Layout';
import BootScreen from './components/BootScreen';
import WelcomeWizard from './components/onboarding/WelcomeWizard';
import TourOverlay from './components/onboarding/TourOverlay';
import { I18nContext, getTranslations } from './lib/i18n';
import type { Language } from './lib/i18n';
import { ThemeContext, getTheme, applyTheme, detective_dark, aurora_light } from './lib/theme';
import WSBridge from './components/WSBridge';

const MissionControl = lazy(() => import('./pages/MissionControl'));
const Activation = lazy(() => import('./pages/Activation'));
const DailyMode = lazy(() => import('./pages/DailyMode'));
const ActionsView = lazy(() => import('./pages/ActionsView'));
const InsightsView = lazy(() => import('./pages/InsightsView'));
const HistoryView = lazy(() => import('./pages/HistoryView'));
const TargetDetail = lazy(() => import('./pages/TargetDetail'));
const EndpointDetail = lazy(() => import('./pages/EndpointDetail'));
const FindingDetail = lazy(() => import('./pages/FindingDetail'));
const IntelligenceDashboard = lazy(() => import('./pages/IntelligenceDashboard'));
const EvidenceCenter = lazy(() => import('./pages/EvidenceCenter'));
const ScreenshotCenter = lazy(() => import('./pages/ScreenshotCenter'));
const ReportCenter = lazy(() => import('./pages/ReportCenter'));
const HypothesisQueue = lazy(() => import('./pages/HypothesisQueue'));
const OpportunityRadar = lazy(() => import('./pages/OpportunityRadar'));
const ConfidenceDashboard = lazy(() => import('./pages/ConfidenceDashboard'));
const OperationsDashboard = lazy(() => import('./pages/OperationsDashboard'));
const TaskQueue = lazy(() => import('./pages/TaskQueue'));
const HotPaths = lazy(() => import('./pages/HotPaths'));
const AttackSurface = lazy(() => import('./pages/AttackSurface'));
const DifferentialEngine = lazy(() => import('./pages/DifferentialEngine'));
const ReplayCenter = lazy(() => import('./pages/ReplayCenter'));
const FindingsPipeline = lazy(() => import('./pages/FindingsPipeline'));
const PersonalIntelligence = lazy(() => import('./pages/PersonalIntelligence'));
const ProjectDashboard = lazy(() => import('./pages/ProjectDashboard'));
const InvestigationCenter = lazy(() => import('./pages/InvestigationCenter'));
const InvestigationDetail = lazy(() => import('./pages/InvestigationDetail'));
const ReportHistory = lazy(() => import('./pages/ReportHistory'));
const ReportDetail = lazy(() => import('./pages/ReportDetail'));
const Settings = lazy(() => import('./pages/Settings'));
const ProgramCatalog = lazy(() => import('./pages/ProgramCatalog'));

const queryClient = new QueryClient({
  defaultOptions: { queries: { refetchOnWindowFocus: false, staleTime: 30_000, gcTime: 10 * 60 * 1000 } },
});

const SETTINGS_KEY = 'rastro-desktop-settings';
const DEFAULT_THEME = 'detective_dark';
const DEFAULT_LANG: Language = 'es';

function detectSystemLanguage(): Language {
  try {
    const navLang = navigator.language?.split('-')[0] ?? '';
    if (navLang === 'es') return 'es';
    if (navLang === 'en') return 'en';
  } catch {}
  return DEFAULT_LANG;
}

function loadSettings(): { theme: string; lang: Language } {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY);
    if (raw) {
      const s = JSON.parse(raw);
      return { theme: s.theme || DEFAULT_THEME, lang: s.lang || DEFAULT_LANG };
    }
  } catch {}
  return { theme: DEFAULT_THEME, lang: detectSystemLanguage() };
}

function saveSettings(theme: string, lang: Language) {
  try {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify({ theme, lang }));
  } catch {}
}

function AuthErrorHandler() {
  const navigate = useNavigate();
  useEffect(() => {
    setOnAuthRedirect((path) => navigate(path, { replace: true }));
    return () => setOnAuthRedirect(null as any);
  }, [navigate]);
  return null;
}

function LicenseGate() {
  const navigate = useNavigate();
  const location = useLocation();
  const { licenseValid } = useLicense();
  useEffect(() => {
    if (licenseValid === false && location.pathname !== '/activate') {
      navigate('/activate', { replace: true });
    }
  }, [licenseValid, navigate, location]);
  return null;
}

function AppInitializer() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { addRecentInvestigation } = useUI();

  useEffect(() => {
    const token = searchParams.get('token');
    const targetId = searchParams.get('target_id');
    console.log('[AppInitializer] URL token param:', token, 'targetId:', targetId, 'href:', window.location.href);

    if (token) {
      console.log('[AppInitializer] calling setAuthToken with:', token);
      setAuthToken(token);
      console.log('[AppInitializer] after setAuthToken, sessionStorage has token:', sessionStorage.getItem('rastro-token'));
    }

    if (targetId) {
      const id = parseInt(targetId, 10);
      if (!isNaN(id)) {
        addRecentInvestigation(id, `Target #${id}`);
      }
    }

    if (token || targetId) {
      console.log('[AppInitializer] navigating to / with replace');
      navigate('/', { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return null;
}

function NotFound() {
  const navigate = useNavigate();
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      height: '100%', gap: 16, color: '#7c8299', padding: 32,
    }}>
      <div style={{
        width: 64, height: 64, borderRadius: 12,
        background: 'linear-gradient(135deg,#7c3aed,#a855f7)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        color: '#fff', fontWeight: 800, fontSize: 28,
      }}>?</div>
      <h1 style={{ fontSize: 24, fontWeight: 700, color: '#e0e0e0', margin: 0 }}>Page Not Found</h1>
      <p style={{ fontSize: 14, color: '#7c8299', textAlign: 'center', maxWidth: 400 }}>
        This investigation path doesn't exist. The mission might have been archived or the location is uncharted.
      </p>
      <button
        onClick={() => navigate('/')}
        style={{
          padding: '10px 24px', borderRadius: 8, border: 'none',
          background: '#7c3aed', color: '#fff', fontSize: 14, fontWeight: 600, cursor: 'pointer',
          marginTop: 8,
        }}
      >Return to Mission Control</button>
    </div>
  );
}

const fallback = (
  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh', color: '#7c8299', fontSize: 14 }}>
    Loading…
  </div>
);

export default function App() {
  const [themeName, setThemeName] = useState(() => loadSettings().theme);
  const [lang, setLang] = useState<Language>(() => loadSettings().lang);
  const [bootComplete, setBootComplete] = useState(() => {
    const val = sessionStorage.getItem('rastro-boot-complete') === 'true';
    console.log('[App] bootComplete initialized to', val, `(sessionStorage key="${sessionStorage.getItem('rastro-boot-complete')}")`);
    return val;
  });
  const { licenseValid, licenseError } = useLicense();

  // Declared unconditionally at the top level — NO early returns before hooks.
  // Initializer functions read URL params / localStorage lazily on first render.
  const [showOnboarding, setShowOnboarding] = useState(
    () => {
      if (localStorage.getItem('rastro-onboarding-complete') === 'true') return false;
      const onboardingParam = new URLSearchParams(window.location.search).get('onboarding');
      return onboardingParam === '1';
    }
  );
  const [showTour, setShowTour] = useState(
    () => localStorage.getItem('rastro-tour-complete') !== 'true'
  );

  const handleBootComplete = useCallback(() => {
    console.log('[App] handleBootComplete called, setting bootComplete=true');
    setBootComplete(true);
    sessionStorage.setItem('rastro-boot-complete', 'true');
  }, []);

  const theme = useMemo(() => getTheme(themeName), [themeName]);

  useEffect(() => {
    applyTheme(theme);
    saveSettings(themeName, lang);
  }, [theme, themeName, lang]);

  const setTheme = useCallback((name: string) => {
    setThemeName(name);
  }, []);

  const setLanguage = useCallback((l: Language) => {
    setLang(l);
  }, []);

  const i18nValue = useMemo(() => ({
    lang,
    t: getTranslations(lang),
    setLang: setLanguage,
  }), [lang, setLanguage]);

  const themeValue = useMemo(() => ({
    theme,
    setTheme,
    available: [detective_dark, aurora_light],
  }), [theme, setTheme]);

  console.log(`[App] render bootComplete=${bootComplete} showOnboarding=${showOnboarding} showTour=${showTour} url=${window.location.href}`);

  if (!bootComplete) {
    const bootErr = licenseValid === false
      ? (licenseError || 'No active license detected. Please activate Rastro to continue.')
      : null;
    return <BootScreen onComplete={handleBootComplete} licenseError={bootErr} />;
  }

  // License gate: if license is known invalid after boot, redirect
  if (licenseValid === false && !showOnboarding && !showTour) {
    return (
      <div style={{
        position: 'fixed', inset: 0, zIndex: 9999,
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        gap: 24, background: '#13151d',
      }}>
        <div style={{
          width: 48, height: 48, borderRadius: '50%',
          background: 'rgba(239,68,68,0.15)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 24,
        }}>⚠</div>
        <div style={{ fontSize: 15, fontWeight: 600, color: '#ef4444' }}>
          License required
        </div>
        <div style={{ fontSize: 13, color: '#7c8299', textAlign: 'center', maxWidth: 360, lineHeight: 1.5 }}>
          {licenseError || 'No active license detected.'}
        </div>
        <button
          onClick={() => window.location.href = '/activate'}
          style={{
            padding: '10px 28px', borderRadius: 8, border: 'none',
            background: '#7c3aed', color: '#fff', fontSize: 14, fontWeight: 600,
            cursor: 'pointer', marginTop: 8,
          }}
        >
          Activate license
        </button>
      </div>
    );
  }

  if (showOnboarding) {
    return (
      <WelcomeWizard onComplete={() => {
        setShowOnboarding(false);
        setShowTour(true);
      }} />
    );
  }

  if (showTour) {
    return <TourOverlay onComplete={() => setShowTour(false)} />;
  }

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeContext.Provider value={themeValue}>
        <I18nContext.Provider value={i18nValue}>
          <GlobalErrorBoundaryUI>
            <StateContinuityProvider>
              <BrowserRouter>
                <AuthErrorHandler />
                <LicenseGate />
                <AppInitializer />
                <WSBridge />
                <Routes>
                  <Route path="/activate" element={<Suspense fallback={fallback}><Activation /></Suspense>} />
                  <Route element={<Layout />}>
                    {/* Mission Hub */}
                    <Route path="/" element={<Suspense fallback={fallback}><MissionControl /></Suspense>} />
                    <Route path="/daily" element={<Suspense fallback={fallback}><DailyMode /></Suspense>} />

                    {/* Recon */}
                    <Route path="/target/:id" element={<Suspense fallback={fallback}><TargetDetail /></Suspense>} />
                    <Route path="/endpoint/:id" element={<Suspense fallback={fallback}><EndpointDetail /></Suspense>} />
                    <Route path="/finding/:id" element={<Suspense fallback={fallback}><FindingDetail /></Suspense>} />
                    <Route path="/surface" element={<Suspense fallback={fallback}><AttackSurface /></Suspense>} />
                    <Route path="/hotpaths" element={<Suspense fallback={fallback}><HotPaths /></Suspense>} />

                    {/* Findings & Evidence */}
                    <Route path="/evidence" element={<Suspense fallback={fallback}><EvidenceCenter /></Suspense>} />
                    <Route path="/screenshots" element={<Suspense fallback={fallback}><ScreenshotCenter /></Suspense>} />
                    <Route path="/pipeline" element={<Suspense fallback={fallback}><FindingsPipeline /></Suspense>} />

                    {/* Analysis */}
                    <Route path="/insights" element={<Suspense fallback={fallback}><InsightsView /></Suspense>} />
                    <Route path="/hypothesis" element={<Suspense fallback={fallback}><HypothesisQueue /></Suspense>} />
                    <Route path="/differential" element={<Suspense fallback={fallback}><DifferentialEngine /></Suspense>} />
                    <Route path="/confidence" element={<Suspense fallback={fallback}><ConfidenceDashboard /></Suspense>} />
                    <Route path="/replay" element={<Suspense fallback={fallback}><ReplayCenter /></Suspense>} />

                    {/* Operations */}
                    <Route path="/actions" element={<Suspense fallback={fallback}><ActionsView /></Suspense>} />
                    <Route path="/operations" element={<Suspense fallback={fallback}><OperationsDashboard /></Suspense>} />
                    <Route path="/tasks" element={<Suspense fallback={fallback}><TaskQueue /></Suspense>} />
                    <Route path="/history" element={<Suspense fallback={fallback}><HistoryView /></Suspense>} />

                    {/* Intelligence */}
                    <Route path="/intelligence" element={<Suspense fallback={fallback}><IntelligenceDashboard /></Suspense>} />
                    <Route path="/personal-intelligence" element={<Suspense fallback={fallback}><PersonalIntelligence /></Suspense>} />
                    <Route path="/radar" element={<Suspense fallback={fallback}><OpportunityRadar /></Suspense>} />
                    <Route path="/programs" element={<Suspense fallback={fallback}><ProgramCatalog /></Suspense>} />
                    <Route path="/reports" element={<Suspense fallback={fallback}><ReportCenter /></Suspense>} />
                    <Route path="/reports/history" element={<Suspense fallback={fallback}><ReportHistory /></Suspense>} />
                    <Route path="/reports/:id" element={<Suspense fallback={fallback}><ReportDetail /></Suspense>} />
                    <Route path="/project-dashboard" element={<Suspense fallback={fallback}><ProjectDashboard /></Suspense>} />
                    <Route path="/investigations" element={<Suspense fallback={fallback}><InvestigationCenter /></Suspense>} />
                    <Route path="/investigation/:id" element={<Suspense fallback={fallback}><InvestigationDetail /></Suspense>} />
                    <Route path="/settings" element={<Suspense fallback={fallback}><Settings /></Suspense>} />

                    {/* 404 */}
                    <Route path="*" element={<NotFound />} />
                  </Route>
                </Routes>
              </BrowserRouter>
            </StateContinuityProvider>
          </GlobalErrorBoundaryUI>
        </I18nContext.Provider>
      </ThemeContext.Provider>
    </QueryClientProvider>
  );
}
