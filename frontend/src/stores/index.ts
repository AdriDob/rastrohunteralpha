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
          console.log('[onRehydrateStorage] inner function called with state:', state ? 'present' : 'null/undefined', 'url:', window.location.href);
          if (state) {
            setHydrating(true);
            Promise.resolve().then(async () => {
              console.log('[onRehydrateStorage] async block started');
              try {
                // Extract token from URL before any API calls to avoid 401 loop
                const urlToken = new URLSearchParams(window.location.search).get('token');
                console.log('[onRehydrateStorage] urlToken from search:', urlToken);
                if (urlToken) {
                  console.log('[onRehydrateStorage] calling setAuthToken from rehydration');
                  const { setAuthToken } = await import('../lib/api');
                  setAuthToken(urlToken);
                  console.log('[onRehydrateStorage] setAuthToken done, sessionStorage rastro-token:', sessionStorage.getItem('rastro-token'));
                }

                // Check license status before proceeding
                console.log('[onRehydrateStorage] checking license status');
                try {
                  const licRes = await fetch('/api/license/status');
                  const licData = await licRes.json();
                  const licValid = licData?.data?.valid === true;
                  console.log('[onRehydrateStorage] license valid:', licValid);
                  if (!licValid) {
                    console.log('[onRehydrateStorage] license invalid — setting licenseValid=false, skipping overview');
                    useStore.setState({ licenseValid: false, licenseLoading: false });
                    setHydrating(false);
                    setHydrated(true);
                    return; // prevent dashboard render
                  }
                } catch (licErr) {
                  console.log('[onRehydrateStorage] license check failed:', licErr);
                  // backend not reachable — keep stale state
                }

                console.log('[onRehydrateStorage] calling getOverviewPreload');
                const { getOverviewPreload } = await import('../lib/api');
                const overview = await getOverviewPreload();
                console.log('[onRehydrateStorage] getOverviewPreload succeeded:', overview);
              } catch (e) {
                console.log('[onRehydrateStorage] getOverviewPreload failed:', e);
                // backend fetch failed — keep stale persisted state
              }
              setHydrating(false);
              setHydrated(true);
              console.log('[onRehydrateStorage] hydration flags set to hydrated');
            });
          }
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
