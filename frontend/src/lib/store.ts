import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { SessionData, NotificationItem } from '../types';

interface RecentInvestigation {
  targetId: number;
  targetName: string;
  timestamp: number;
}

interface UIState {
  sidebarCollapsed: boolean;
  sidebarOpen: boolean;
  toggleSidebar: () => void;
  setSidebarOpen: (v: boolean) => void;
  activeMissionId: string | null;
  setActiveMission: (id: string | null) => void;
  assistantOpen: boolean;
  setAssistantOpen: (v: boolean) => void;
  commandPaletteOpen: boolean;
  setCommandPaletteOpen: (v: boolean) => void;
}

interface SelectionState {
  selectedTargetId: number | null;
  selectedEndpointId: number | null;
  selectedFindingId: number | null;
  setSelectedTarget: (id: number | null) => void;
  setSelectedEndpoint: (id: number | null) => void;
  setSelectedFinding: (id: number | null) => void;
  clearAll: () => void;
}

interface OperationsState {
  session: SessionData | null;
  notifications: NotificationItem[];
  unreadCount: number;
  setSession: (s: SessionData | null) => void;
  setNotifications: (n: NotificationItem[]) => void;
  setUnreadCount: (c: number) => void;
  markRead: (id: number) => void;
  markAllRead: () => void;
}

interface RecentState {
  recentInvestigations: RecentInvestigation[];
  addRecentInvestigation: (targetId: number, targetName: string) => void;
  clearRecent: () => void;
  favoriteTargets: number[];
  toggleFavoriteTarget: (targetId: number) => void;
}

interface ObservabilityState {
  commandPaletteUsage: number;
  assistantInvocations: number;
  recommendedActionsAccepted: number;
  incrementCommandPaletteUsage: () => void;
  incrementAssistantInvocations: () => void;
  incrementRecommendedActionsAccepted: () => void;
  resetObservability: () => void;
}

export type AppStore = SelectionState & OperationsState & UIState & RecentState & ObservabilityState;

export const useStore = create<AppStore>()(
  persist(
    (set) => ({
      // ── Selection ──────────────────────────────────────────────────
      selectedTargetId: null,
      selectedEndpointId: null,
      selectedFindingId: null,
      setSelectedTarget: (id) => set({ selectedTargetId: id, selectedEndpointId: null, selectedFindingId: null }),
      setSelectedEndpoint: (id) => set({ selectedEndpointId: id, selectedFindingId: null }),
      setSelectedFinding: (id) => set({ selectedFindingId: id }),
      clearAll: () => set({ selectedTargetId: null, selectedEndpointId: null, selectedFindingId: null }),

      // ── UI State ───────────────────────────────────────────────────
      sidebarCollapsed: false,
      sidebarOpen: true,
      toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
      setSidebarOpen: (v) => set({ sidebarOpen: v }),
      activeMissionId: null,
      setActiveMission: (id) => set({ activeMissionId: id }),
      assistantOpen: false,
      setAssistantOpen: (v) => set({ assistantOpen: v }),
      commandPaletteOpen: false,
      setCommandPaletteOpen: (v) => set({ commandPaletteOpen: v }),

      // ── Operations ─────────────────────────────────────────────────
      session: null,
      notifications: [],
      unreadCount: 0,
      setSession: (s) => set({ session: s }),
      setNotifications: (n) => set({ notifications: n, unreadCount: n.filter(x => !x.is_read).length }),
      setUnreadCount: (c) => set({ unreadCount: c }),
      markRead: (id) => set((s) => ({
        notifications: s.notifications.map(n => n.id === id ? { ...n, is_read: true } : n),
        unreadCount: Math.max(0, s.unreadCount - 1),
      })),
      markAllRead: () => set((s) => ({
        notifications: s.notifications.map(n => ({ ...n, is_read: true })),
        unreadCount: 0,
      })),

      // ── Recent Investigations ──────────────────────────────────────
      recentInvestigations: [],
      addRecentInvestigation: (targetId, targetName) => set((s) => {
        const filtered = s.recentInvestigations.filter(r => r.targetId !== targetId);
        return {
          recentInvestigations: [
            { targetId, targetName, timestamp: Date.now() },
            ...filtered,
          ].slice(0, 10),
        };
      }),
      clearRecent: () => set({ recentInvestigations: [] }),
      favoriteTargets: [],
      toggleFavoriteTarget: (targetId) => set((s) => {
        const exists = s.favoriteTargets.includes(targetId);
        return {
          favoriteTargets: exists
            ? s.favoriteTargets.filter(id => id !== targetId)
            : [...s.favoriteTargets, targetId],
        };
      }),

      // ── Observability ──────────────────────────────────────────────
      commandPaletteUsage: 0,
      assistantInvocations: 0,
      recommendedActionsAccepted: 0,
      incrementCommandPaletteUsage: () => set((s) => ({ commandPaletteUsage: s.commandPaletteUsage + 1 })),
      incrementAssistantInvocations: () => set((s) => ({ assistantInvocations: s.assistantInvocations + 1 })),
      incrementRecommendedActionsAccepted: () => set((s) => ({ recommendedActionsAccepted: s.recommendedActionsAccepted + 1 })),
      resetObservability: () => set({ commandPaletteUsage: 0, assistantInvocations: 0, recommendedActionsAccepted: 0 }),
    }),
    {
      name: 'rastro-store',
      partialize: (state) => ({
        sidebarCollapsed: state.sidebarCollapsed,
        activeMissionId: state.activeMissionId,
        recentInvestigations: state.recentInvestigations,
        favoriteTargets: state.favoriteTargets,
        session: state.session,
        selectedTargetId: state.selectedTargetId,
      }),
    },
  ),
);
