import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { useShallow } from 'zustand/react/shallow';
import { createAuthSlice } from './authSlice';
import type { AuthSlice } from './authSlice';
import { createLicenseSlice } from './licenseSlice';
import type { LicenseSlice } from './licenseSlice';
import { createDashboardSlice } from './dashboardSlice';
import type { DashboardSlice } from './dashboardSlice';
import { createWSSlice } from './wsSlice';
import type { WSSlice } from './wsSlice';
import { createUISlice } from './uiSlice';
import type { UISlice } from './uiSlice';

export type { WSConnectionStatus } from './wsSlice';

export type AppStore = AuthSlice & LicenseSlice & DashboardSlice & WSSlice & UISlice;

function setHydrating(v: boolean) {
  useStore.setState({ hydrating: v } as Partial<AppStore>);
}
function setHydrated(v: boolean) {
  useStore.setState({ hydrated: v } as Partial<AppStore>);
}

export const useStore = create<AppStore>()(
  persist(
    (...a) => ({
      ...createAuthSlice(...a),
      ...createLicenseSlice(...a),
      ...createDashboardSlice(...a),
      ...createWSSlice(...a),
      ...createUISlice(...a),
    }),
    {
      name: 'rastro-store',
      partialize: (state) => ({
        session: state.session,
        licenseValid: state.licenseValid,
        licenseLoading: state.licenseLoading,
        licenseError: state.licenseError,
        sidebarCollapsed: state.sidebarCollapsed,
        activeMissionId: state.activeMissionId,
        recentInvestigations: state.recentInvestigations,
        favoriteTargets: state.favoriteTargets,
        commandPaletteUsage: state.commandPaletteUsage,
        assistantInvocations: state.assistantInvocations,
        recommendedActionsAccepted: state.recommendedActionsAccepted,
      }),
      onRehydrateStorage: () => {
        return (state) => {
          console.log('BUILD 27 - INNER CALLED state=', state ? 'present' : 'null/undefined', 'url=', window.location.href);
          console.log('BUILD 27 - rastro-token at entry:', sessionStorage.getItem('rastro-token'));
          if (!state) {
            console.log('[onRehydrateStorage] RETURN EARLY — state was falsy');
            return;
          }
          console.log('[onRehydrateStorage] state present — calling setHydrating(true)');
          setHydrating(true);
          Promise.resolve().then(async () => {
            console.log('[onRehydrateStorage] ASYNC BLOCK ENTERED');
            try {
              const urlToken = new URLSearchParams(window.location.search).get('token');
              console.log('[onRehydrateStorage] urlToken:', JSON.stringify(urlToken));

              if (urlToken) {
                console.log('[onRehydrateStorage] BRANCH A: urlToken present — calling setAuthToken');
                const { setAuthToken } = await import('../lib/api');
                setAuthToken(urlToken);
                const afterSet = sessionStorage.getItem('rastro-token');
                console.log('[onRehydrateStorage] BRANCH A: after setAuthToken, rastro-token=', afterSet ? 'present (' + afterSet.slice(0, 8) + '...)' : 'STILL NULL');
              } else {
                const existing = sessionStorage.getItem('rastro-token');
                console.log('[onRehydrateStorage] BRANCH B: no urlToken, existing rastro-token=', existing ? 'present (' + existing.slice(0, 8) + '...)' : 'null');
              }

              // license check
              console.log('[onRehydrateStorage] BEFORE license fetch');
              let licValid = false;
              try {
                const licRes = await fetch('/api/license/status');
                console.log('[onRehydrateStorage] license fetch status:', licRes.status);
                const licData = await licRes.json();
                console.log('[onRehydrateStorage] license fetch body:', JSON.stringify(licData));
                licValid = licData?.data?.valid === true;
                console.log('[onRehydrateStorage] licValid =', licValid);
              } catch (licErr) {
                console.log('[onRehydrateStorage] license fetch EXCEPTION:', licErr);
              }

              if (!licValid) {
                console.log('[onRehydrateStorage] RETURN — license invalid, setting licenseValid=false');
                useStore.setState({ licenseValid: false, licenseLoading: false });
                setHydrating(false);
                setHydrated(true);
                console.log('[onRehydrateStorage] RETURN DONE (license invalid)');
                return;
              }

              console.log('[onRehydrateStorage] CONTINUE — license valid');
              const tokenBefore = sessionStorage.getItem('rastro-token');
              console.log('[onRehydrateStorage] tokenBefore dashboard call:', tokenBefore ? 'present (' + tokenBefore.slice(0, 8) + '...)' : 'null');

              if (!tokenBefore && !urlToken) {
                console.log('[onRehydrateStorage] BRANCH C: no token anywhere — attempting auto-login');
                try {
                  let deviceId = localStorage.getItem('rastro-device-id');
                  console.log('[onRehydrateStorage] auto-login deviceId from localStorage:', deviceId);
                  if (!deviceId) {
                    deviceId = 'web-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 8);
                    localStorage.setItem('rastro-device-id', deviceId);
                    console.log('[onRehydrateStorage] auto-login generated new deviceId:', deviceId);
                  }
                  const requestBody = JSON.stringify({ device_id: deviceId, device_info: { source: 'browser' } });
                  console.log('[onRehydrateStorage] auto-login REQUEST body:', requestBody);
                  const loginRes = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: requestBody,
                  });
                  console.log('[onRehydrateStorage] auto-login RESPONSE status:', loginRes.status);
                  let loginData: any;
                  try {
                    loginData = await loginRes.json();
                    console.log('[onRehydrateStorage] auto-login RESPONSE body:', JSON.stringify(loginData));
                  } catch (parseErr) {
                    console.log('[onRehydrateStorage] auto-login JSON parse ERROR:', parseErr);
                    const text = await loginRes.text();
                    console.log('[onRehydrateStorage] auto-login RAW body:', text);
                    loginData = null;
                  }
                  if (loginData?.data?.token) {
                    console.log('[onRehydrateStorage] auto-login SUCCESS — token found, calling setAuthToken');
                    const { setAuthToken } = await import('../lib/api');
                    setAuthToken(loginData.data.token);
                    const afterLogin = sessionStorage.getItem('rastro-token');
                    console.log('[onRehydrateStorage] auto-login — after setAuthToken, rastro-token=', afterLogin ? 'present (' + afterLogin.slice(0, 8) + '...)' : 'STILL NULL');
                  } else {
                    console.log('[onRehydrateStorage] auto-login FAIL — response had no token');
                    if (loginData?.error) {
                      console.log('[onRehydrateStorage] auto-login server error:', loginData.error);
                    }
                  }
                } catch (loginErr) {
                  console.log('[onRehydrateStorage] auto-login FETCH EXCEPTION:', loginErr);
                }
              } else {
                console.log('[onRehydrateStorage] BRANCH D: token already present — skipping auto-login (tokenBefore=', !!tokenBefore, 'urlToken=', !!urlToken, ')');
              }

              console.log('[onRehydrateStorage] BEFORE getOverviewPreload');
              const tokenFinal = sessionStorage.getItem('rastro-token');
              console.log('[onRehydrateStorage] token before overview call:', tokenFinal ? 'present (' + tokenFinal.slice(0, 8) + '...)' : 'null');
              try {
                const { getOverviewPreload } = await import('../lib/api');
                const overview = await getOverviewPreload();
                console.log('[onRehydrateStorage] getOverviewPreload SUCCESS:', overview ? 'data received' : 'null');
              } catch (overviewErr) {
                console.log('[onRehydrateStorage] getOverviewPreload EXCEPTION:', overviewErr);
              }
            } catch (e) {
              console.log('[onRehydrateStorage] TOP-LEVEL EXCEPTION:', e);
            }
            setHydrating(false);
            setHydrated(true);
            console.log('[onRehydrateStorage] ASYNC BLOCK COMPLETE — hydrating=false, hydrated=true');
          });
        };
      },
    },
  ),
);

export const useAuth = () => useStore(useShallow((s) => ({
  session: s.session,
  setSession: s.setSession,
})));

export const useLicense = () => useStore(useShallow((s) => ({
  licenseValid: s.licenseValid,
  licenseLoading: s.licenseLoading,
  licenseError: s.licenseError,
  setLicenseValid: s.setLicenseValid,
  setLicenseLoading: s.setLicenseLoading,
  setLicenseError: s.setLicenseError,
})));

export const useDashboard = () => useStore(useShallow((s) => ({
  overview: s.overview,
  overviewLoading: s.overviewLoading,
  overviewError: s.overviewError,
  favorites: s.favorites,
  favoritesLoading: s.favoritesLoading,
  notifications: s.notifications,
  unreadCount: s.unreadCount,
  fetchOverview: s.fetchOverview,
  fetchFavorites: s.fetchFavorites,
  fetchNotifications: s.fetchNotifications,
  setNotificationsDirect: s.setNotificationsDirect,
  setUnreadCountDirect: s.setUnreadCountDirect,
  markRead: s.markRead,
  markAllRead: s.markAllRead,
  addNotification: s.addNotification,
})));

export const useWS = () => useStore(useShallow((s) => ({
  wsConnected: s.wsConnected,
  wsRetries: s.wsRetries,
  wsLastMessage: s.wsLastMessage,
  setWSConnected: s.setWSConnected,
  setWSRetries: s.setWSRetries,
  setWSLastMessage: s.setWSLastMessage,
})));

export const useUI = () => useStore(useShallow((s) => ({
  sidebarCollapsed: s.sidebarCollapsed,
  sidebarOpen: s.sidebarOpen,
  toggleSidebar: s.toggleSidebar,
  setSidebarOpen: s.setSidebarOpen,
  activeMissionId: s.activeMissionId,
  setActiveMission: s.setActiveMission,
  assistantOpen: s.assistantOpen,
  setAssistantOpen: s.setAssistantOpen,
  commandPaletteOpen: s.commandPaletteOpen,
  setCommandPaletteOpen: s.setCommandPaletteOpen,
  selectedTargetId: s.selectedTargetId,
  selectedEndpointId: s.selectedEndpointId,
  selectedFindingId: s.selectedFindingId,
  setSelectedTarget: s.setSelectedTarget,
  setSelectedEndpoint: s.setSelectedEndpoint,
  setSelectedFinding: s.setSelectedFinding,
  clearAll: s.clearAll,
  recentInvestigations: s.recentInvestigations,
  addRecentInvestigation: s.addRecentInvestigation,
  clearRecent: s.clearRecent,
  favoriteTargets: s.favoriteTargets,
  toggleFavoriteTarget: s.toggleFavoriteTarget,
  commandPaletteUsage: s.commandPaletteUsage,
  assistantInvocations: s.assistantInvocations,
  recommendedActionsAccepted: s.recommendedActionsAccepted,
  incrementCommandPaletteUsage: s.incrementCommandPaletteUsage,
  incrementAssistantInvocations: s.incrementAssistantInvocations,
  incrementRecommendedActionsAccepted: s.incrementRecommendedActionsAccepted,
  resetObservability: s.resetObservability,
})));
