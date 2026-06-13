/**
 * System state and event hooks — the live pulse of Rastro.
 * Polls /api/system/state for real-time health awareness.
 */

import { useQuery } from '@tanstack/react-query';
import { fetchJson } from '../api';

export interface SystemStateSummary {
  system_state: 'BOOTING' | 'READY' | 'DEGRADED' | 'FAILED';
  uptime_seconds: number;
  services_total: number;
  services_healthy: number;
  services_unhealthy: number;
  boot_start: number;
}

export interface ServiceInfo {
  name: string;
  state: string;
  last_healthy: number | null;
  last_seen: number | null;
  error_count: number;
  last_error: string | null;
}

export interface SystemStateResponse {
  state: SystemStateSummary;
  services: ServiceInfo[];
}

export interface SystemEvent {
  type: string;
  timestamp: number;
  payload: Record<string, unknown>;
}

const POLL_INTERVAL = 5000;

function fetchSystemState(): Promise<SystemStateResponse> {
  return fetchJson<SystemStateResponse>('/system/state');
}

function fetchSystemEvents(eventType?: string, limit = 20): Promise<{ events: SystemEvent[]; total: number }> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (eventType) params.set('event_type', eventType);
  return fetchJson(`/system/state/events?${params}`);
}

export function useSystemState() {
  return useQuery({
    queryKey: ['systemState'],
    queryFn: fetchSystemState,
    refetchInterval: POLL_INTERVAL,
    staleTime: POLL_INTERVAL - 1000,
  });
}

export function useSystemEvents(eventType?: string, limit = 20) {
  return useQuery({
    queryKey: ['systemEvents', eventType, limit],
    queryFn: () => fetchSystemEvents(eventType, limit),
    refetchInterval: POLL_INTERVAL,
    staleTime: POLL_INTERVAL - 1000,
  });
}

/** Formats uptime in human-readable format. */
export function formatUptime(seconds: number): string {
  if (seconds < 60) return `${Math.floor(seconds)}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.floor(seconds % 60)}s`;
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${h}h ${m}m`;
}

/** Derives a color from system state. */
export function stateColor(state: string): string {
  switch (state) {
    case 'READY': return '#22c55e';
    case 'DEGRADED': return '#f59e0b';
    case 'FAILED': return '#ef4444';
    default: return '#6b7280';
  }
}
