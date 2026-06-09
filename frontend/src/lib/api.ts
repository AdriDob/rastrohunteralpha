import type { PaginatedResult, PaginationFilters } from '../types';

const BASE = '/api';

async function fetchJson<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, opts);
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
}

function toQuery(filters?: PaginationFilters): string {
  if (!filters) return '';
  const p = new URLSearchParams();
  if (filters.skip !== undefined) p.set('skip', String(filters.skip));
  if (filters.limit !== undefined) p.set('limit', String(filters.limit));
  if (filters.sort_by) p.set('sort_by', filters.sort_by);
  if (filters.sort_order) p.set('sort_order', filters.sort_order);
  if (filters.search) p.set('search', filters.search);
  const s = p.toString();
  return s ? `?${s}` : '';
}

export function getTargets(filters?: PaginationFilters) {
  return fetchJson<PaginatedResult<import('../types').Target>>(`/targets${toQuery(filters)}`);
}

export function getTarget(id: number) {
  return fetchJson<import('../types').TargetSummary>(`/targets/${id}`);
}

export function getEndpoints(targetId?: number, filters?: PaginationFilters) {
  const p = new URLSearchParams();
  if (targetId) p.set('target_id', String(targetId));
  if (filters?.skip !== undefined) p.set('skip', String(filters.skip));
  if (filters?.limit !== undefined) p.set('limit', String(filters.limit));
  if (filters?.sort_by) p.set('sort_by', filters.sort_by);
  if (filters?.sort_order) p.set('sort_order', filters.sort_order);
  if (filters?.search) p.set('search', filters.search);
  const q = p.toString() ? `?${p}` : '';
  return fetchJson<PaginatedResult<import('../types').Endpoint>>(`/endpoints${q}`);
}

export function getEndpoint(id: number) {
  return fetchJson<import('../types').Endpoint>(`/endpoints/${id}`);
}

export function getFindings(targetId?: number, endpointId?: number, filters?: PaginationFilters) {
  const p = new URLSearchParams();
  if (targetId) p.set('target_id', String(targetId));
  if (endpointId) p.set('endpoint_id', String(endpointId));
  if (filters?.skip !== undefined) p.set('skip', String(filters.skip));
  if (filters?.limit !== undefined) p.set('limit', String(filters.limit));
  if (filters?.sort_by) p.set('sort_by', filters.sort_by);
  if (filters?.sort_order) p.set('sort_order', filters.sort_order);
  if (filters?.search) p.set('search', filters.search);
  const q = p.toString() ? `?${p}` : '';
  return fetchJson<PaginatedResult<import('../types').Finding>>(`/findings${q}`);
}

export function getEvidence(verdictId?: number, filters?: PaginationFilters) {
  const p = new URLSearchParams();
  if (verdictId) p.set('verdict_id', String(verdictId));
  if (filters?.skip !== undefined) p.set('skip', String(filters.skip));
  if (filters?.limit !== undefined) p.set('limit', String(filters.limit));
  if (filters?.sort_by) p.set('sort_by', filters.sort_by);
  if (filters?.sort_order) p.set('sort_order', filters.sort_order);
  if (filters?.search) p.set('search', filters.search);
  const q = p.toString() ? `?${p}` : '';
  return fetchJson<PaginatedResult<import('../types').Evidence>>(`/evidence${q}`);
}

export function getOpportunities(filters?: PaginationFilters) {
  return fetchJson<PaginatedResult<import('../types').Opportunity>>(`/opportunities${toQuery(filters)}`);
}

export function getTargetROI(targetId: number) {
  return fetchJson<import('../types').TargetROI>(`/roi/${targetId}`);
}

export function getAttackSurfaces() {
  return fetchJson<import('../types').AttackSurfaceMap>('/attack-surface');
}

export function getPipeline() {
  return fetchJson<import('../types').PipelineStages>('/pipeline');
}

export function runHypotheses(targetId: number) {
  return fetchJson<import('../types').HypothesisEngineOutput>(`/hypotheses/${targetId}`, { method: 'POST' });
}

export function getReport() {
  return fetchJson<import('../types').Report>('/reports/generate');
}
