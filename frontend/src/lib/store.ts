import { create } from 'zustand';

interface SelectionState {
  selectedTargetId: number | null;
  selectedEndpointId: number | null;
  selectedFindingId: number | null;
  setSelectedTarget: (id: number | null) => void;
  setSelectedEndpoint: (id: number | null) => void;
  setSelectedFinding: (id: number | null) => void;
  clearAll: () => void;
}

export const useStore = create<SelectionState>((set) => ({
  selectedTargetId: null,
  selectedEndpointId: null,
  selectedFindingId: null,
  setSelectedTarget: (id) => set({ selectedTargetId: id, selectedEndpointId: null, selectedFindingId: null }),
  setSelectedEndpoint: (id) => set({ selectedEndpointId: id, selectedFindingId: null }),
  setSelectedFinding: (id) => set({ selectedFindingId: id }),
  clearAll: () => set({ selectedTargetId: null, selectedEndpointId: null, selectedFindingId: null }),
}));
