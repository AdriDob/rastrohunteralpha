import type { StateCreator } from 'zustand';

interface RecentInvestigation {
  targetId: number;
  targetName: string;
  timestamp: number;
}

export interface UISlice {
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

  selectedTargetId: number | null;
  selectedEndpointId: number | null;
  selectedFindingId: number | null;
  setSelectedTarget: (id: number | null) => void;
  setSelectedEndpoint: (id: number | null) => void;
  setSelectedFinding: (id: number | null) => void;
  clearAll: () => void;

  recentInvestigations: RecentInvestigation[];
  addRecentInvestigation: (targetId: number, targetName: string) => void;
  clearRecent: () => void;
  favoriteTargets: number[];
  toggleFavoriteTarget: (targetId: number) => void;

  commandPaletteUsage: number;
  assistantInvocations: number;
  recommendedActionsAccepted: number;
  incrementCommandPaletteUsage: () => void;
  incrementAssistantInvocations: () => void;
  incrementRecommendedActionsAccepted: () => void;
  resetObservability: () => void;
}

export const createUISlice: StateCreator<UISlice, [], [], UISlice> = (set) => ({
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

  selectedTargetId: null,
  selectedEndpointId: null,
  selectedFindingId: null,
  setSelectedTarget: (id) => set({ selectedTargetId: id, selectedEndpointId: null, selectedFindingId: null }),
  setSelectedEndpoint: (id) => set({ selectedEndpointId: id, selectedFindingId: null }),
  setSelectedFinding: (id) => set({ selectedFindingId: id }),
  clearAll: () => set({ selectedTargetId: null, selectedEndpointId: null, selectedFindingId: null }),

  recentInvestigations: [],
  addRecentInvestigation: (targetId, targetName) => set((s) => {
    const filtered = s.recentInvestigations.filter((r) => r.targetId !== targetId);
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
        ? s.favoriteTargets.filter((id) => id !== targetId)
        : [...s.favoriteTargets, targetId],
    };
  }),

  commandPaletteUsage: 0,
  assistantInvocations: 0,
  recommendedActionsAccepted: 0,
  incrementCommandPaletteUsage: () => set((s) => ({ commandPaletteUsage: s.commandPaletteUsage + 1 })),
  incrementAssistantInvocations: () => set((s) => ({ assistantInvocations: s.assistantInvocations + 1 })),
  incrementRecommendedActionsAccepted: () => set((s) => ({ recommendedActionsAccepted: s.recommendedActionsAccepted + 1 })),
  resetObservability: () => set({ commandPaletteUsage: 0, assistantInvocations: 0, recommendedActionsAccepted: 0 }),
});
