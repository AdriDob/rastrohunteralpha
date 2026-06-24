import type { StateCreator } from 'zustand';

export type WSConnectionStatus = 'disconnected' | 'connecting' | 'connected';

export interface WSSlice {
  wsConnected: WSConnectionStatus;
  wsRetries: number;
  wsLastMessage: unknown;
  setWSConnected: (s: WSConnectionStatus) => void;
  setWSRetries: (n: number) => void;
  setWSLastMessage: (m: unknown) => void;
}

export const createWSSlice: StateCreator<WSSlice, [], [], WSSlice> = (set) => ({
  wsConnected: 'disconnected',
  wsRetries: 0,
  wsLastMessage: null,
  setWSConnected: (s) => set({ wsConnected: s }),
  setWSRetries: (n) => set({ wsRetries: n }),
  setWSLastMessage: (m) => set({ wsLastMessage: m }),
});
