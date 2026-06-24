export interface HydrationSlice {
  hydrating: boolean;
  hydrated: boolean;
  setHydrating: (v: boolean) => void;
  setHydrated: (v: boolean) => void;
}

export const initialHydrationState = {
  hydrating: true,
  hydrated: false,
};

export const createHydrationSlice = (
  set: (partial: Partial<HydrationSlice>) => void,
): HydrationSlice => ({
  ...initialHydrationState,
  setHydrating: (v) => set({ hydrating: v }),
  setHydrated: (v) => set({ hydrated: v }),
});
