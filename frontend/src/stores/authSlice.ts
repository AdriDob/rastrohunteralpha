import type { StateCreator } from 'zustand';
import type { SessionData } from '../types';

export interface AuthSlice {
  session: SessionData | null;
  setSession: (s: SessionData | null) => void;
}

export const createAuthSlice: StateCreator<AuthSlice, [], [], AuthSlice> = (set) => ({
  session: null,
  setSession: (s) => set({ session: s }),
});
