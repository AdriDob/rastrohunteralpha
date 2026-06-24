import type { StateCreator } from 'zustand';
import type { OverviewData, NotificationItem } from '../types';
import { getOverview, getFavorites, getNotifications } from '../lib/api';

export interface DashboardSlice {
  overview: OverviewData | null;
  overviewLoading: boolean;
  overviewError: string | null;
  favorites: { item_type: string; item_id: number; id: number }[];
  favoritesLoading: boolean;
  notifications: NotificationItem[];
  unreadCount: number;
  fetchOverview: () => Promise<void>;
  fetchFavorites: (itemType?: string) => Promise<void>;
  fetchNotifications: (unreadOnly?: boolean) => Promise<NotificationItem[]>;
  setNotificationsDirect: (items: NotificationItem[]) => void;
  setUnreadCountDirect: (c: number) => void;
  markRead: (id: number) => void;
  markAllRead: () => void;
  addNotification: (n: NotificationItem) => void;
}

export const createDashboardSlice: StateCreator<DashboardSlice, [], [], DashboardSlice> = (set) => ({
  overview: null,
  overviewLoading: false,
  overviewError: null,
  favorites: [],
  favoritesLoading: false,
  notifications: [],
  unreadCount: 0,

  fetchOverview: async () => {
    set({ overviewLoading: true, overviewError: null });
    try {
      const data = await getOverview();
      set({ overview: data, overviewLoading: false });
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to load overview';
      set({ overviewError: msg, overviewLoading: false });
    }
  },

  fetchFavorites: async (itemType?: string) => {
    set({ favoritesLoading: true });
    try {
      const r = await getFavorites(itemType);
      set({ favorites: r?.items ?? [], favoritesLoading: false });
    } catch {
      set({ favoritesLoading: false });
    }
  },

  fetchNotifications: async (unreadOnly?: boolean) => {
    try {
      const r = await getNotifications(unreadOnly);
      const items = r?.items ?? [];
      set({ notifications: items, unreadCount: items.filter((x) => !x.is_read).length });
      return items;
    } catch {
      return [];
    }
  },

  setNotificationsDirect: (items) => set({
    notifications: items,
    unreadCount: items.filter((x) => !x.is_read).length,
  }),

  setUnreadCountDirect: (c) => set({ unreadCount: c }),

  markRead: (id) => set((s) => ({
    notifications: s.notifications.map((n) => (n.id === id ? { ...n, is_read: true } : n)),
    unreadCount: Math.max(0, s.unreadCount - 1),
  })),

  markAllRead: () => set((s) => ({
    notifications: s.notifications.map((n) => ({ ...n, is_read: true })),
    unreadCount: 0,
  })),

  addNotification: (n) => set((s) => ({
    notifications: [n, ...s.notifications].slice(0, 50),
    unreadCount: s.unreadCount + (n.is_read ? 0 : 1),
  })),
});
