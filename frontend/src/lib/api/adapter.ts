/**
 * Frontend API Adapter Layer.
 *
 * Every raw API response passes through here before reaching UI components.
 * This guarantees:
 *   - Stable camelCase DTOs regardless of backend field naming
 *   - Safe defaults (no undefined/null propagation)
 *   - Decoupling: backend can evolve without breaking frontend
 */

import type {
  TargetDTO,
  OpportunityDTO,
  EndpointDTO,
  FindingDTO,
  EvidenceDTO,
  OverviewDTO,
  PaginatedDTO,
} from '../../types';

// ── Helpers ──────────────────────────────────────────────────────────

function safeInt(v: unknown, d = 0): number {
  if (v === null || v === undefined) return d;
  const n = Number(v);
  return Number.isFinite(n) ? n : d;
}

function safeFloat(v: unknown, d = 0.0): number {
  if (v === null || v === undefined) return d;
  const n = Number(v);
  return Number.isFinite(n) ? n : d;
}

function safeStr(v: unknown, d = ''): string {
  if (v === null || v === undefined) return d;
  return String(v);
}

function safeArr<T>(v: unknown, d: T[] = []): T[] {
  return Array.isArray(v) ? v : d;
}

function safeBool(v: unknown): boolean {
  return v === true || v === 1 || v === 'true';
}

// ── snake_case → camelCase ──────────────────────────────────────────

function toCamel(key: string): string {
  if (!key.includes('_')) return key;
  const parts = key.split('_');
  return parts[0] + parts.slice(1).map(p => p.charAt(0).toUpperCase() + p.slice(1)).join('');
}

// ── Copiar normalizer logic from core/contracts/normalizers.py ───────

const TARGET_MAP: Record<string, string> = {
  estimated_payout: 'payout',
  opportunity_score: 'score',
  risk_score: 'risk',
  endpoint_count: 'endpoints',
  finding_count: 'findings',
  confirmed_findings: 'confirmedFindings',
  competition_score: 'competition',
  freshness_score: 'freshness',
  created_at: 'createdAt',
  last_updated: 'lastUpdated',
};

const OPPORTUNITY_MAP: Record<string, string> = {
  estimated_payout: 'payout',
  opportunity_score: 'score',
  competition_score: 'competition',
  freshness_score: 'freshness',
  target_id: 'targetId',
  endpoint_count: 'endpoints',
  finding_count: 'findings',
  max_risk: 'risk',
  created_at: 'createdAt',
  last_update: 'lastUpdated',
};

const ENDPOINT_MAP: Record<string, string> = {
  target_id: 'targetId',
  risk_score: 'risk',
  created_at: 'createdAt',
  attack_surface: 'attackSurface',
};

const FINDING_MAP: Record<string, string> = {
  target_id: 'targetId',
  endpoint_id: 'endpointId',
  estimated_payout: 'payout',
  risk_score: 'risk',
  created_at: 'createdAt',
  confirmed_at: 'confirmedAt',
};

const EVIDENCE_MAP: Record<string, string> = {
  verdict_id: 'verdictId',
  finding_id: 'findingId',
  request_url: 'requestUrl',
  response_status: 'responseStatus',
  request_body: 'requestBody',
  response_body: 'responseBody',
  request_headers: 'requestHeaders',
  response_headers: 'responseHeaders',
  created_at: 'createdAt',
};

const OVERVIEW_MAP: Record<string, string> = {
  target_count: 'targets',
  endpoint_count: 'endpoints',
  finding_count: 'findings',
  confirmed_verdicts: 'confirmed',
  active_scans: 'activeScans',
  high_signal_endpoints: 'highSignal',
  avg_risk_score: 'avgRisk',
  risk_distribution: 'riskDistribution',
  vector_distribution: 'vectorDistribution',
  severity_counts: 'severity',
  pipeline_stages: 'pipeline',
};

function applyMap(raw: Record<string, unknown>, map: Record<string, string>): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(raw)) {
    const mapped = map[key] ?? toCamel(key);
    out[mapped] = value;
  }
  return out;
}

// ── Normalizers ──────────────────────────────────────────────────────

export function normalizeTarget(raw: Record<string, unknown> | null | undefined): TargetDTO {
  if (!raw) return emptyTarget();
  const m = applyMap(raw, TARGET_MAP);
  return {
    id: safeInt(m.id),
    name: safeStr(m.name),
    domain: safeStr(m.domain),
    payout: safeInt(m.payout),
    score: safeFloat(m.score),
    risk: safeFloat(m.risk),
    roi: safeFloat(m.roi),
    endpoints: safeInt(m.endpoints),
    findings: safeInt(m.findings),
    confirmedFindings: safeInt(m.confirmedFindings),
    competition: safeFloat(m.competition),
    freshness: safeFloat(m.freshness),
  };
}

export function normalizeOpportunity(raw: Record<string, unknown> | null | undefined): OpportunityDTO {
  if (!raw) return emptyOpportunity();
  const m = applyMap(raw, OPPORTUNITY_MAP);
  return {
    id: safeInt(m.id),
    targetId: safeInt(m.targetId),
    name: safeStr(m.name),
    domain: safeStr(m.domain),
    payout: safeInt(m.payout),
    score: safeFloat(m.score),
    risk: safeFloat(m.risk),
    roi: safeFloat(m.roi),
    endpoints: safeInt(m.endpoints),
    findings: safeInt(m.findings),
    competition: safeFloat(m.competition),
    freshness: safeFloat(m.freshness),
    surfaces: safeArr<string>(m.surfaces),
    vectors: safeArr<string>(m.vectors),
  };
}

export function normalizeEndpoint(raw: Record<string, unknown> | null | undefined): EndpointDTO {
  if (!raw) return emptyEndpoint();
  const m = applyMap(raw, ENDPOINT_MAP);
  return {
    id: safeInt(m.id),
    targetId: safeInt(m.targetId),
    path: safeStr(m.path),
    method: safeStr(m.method),
    risk: safeFloat(m.risk),
    confidence: safeFloat(m.confidence),
    vector: safeStr(m.vector),
    labels: safeArr<string>(m.labels),
    signals: safeArr<string>(m.signals),
    attackSurface: safeArr<string>(m.attackSurface),
    actionable: safeBool(m.actionable),
  };
}

export function normalizeFinding(raw: Record<string, unknown> | null | undefined): FindingDTO {
  if (!raw) return emptyFinding();
  const m = applyMap(raw, FINDING_MAP);
  return {
    id: safeInt(m.id),
    targetId: safeInt(m.targetId),
    endpointId: safeInt(m.endpointId),
    title: safeStr(m.title),
    severity: safeStr(m.severity),
    confidence: safeFloat(m.confidence),
    status: safeStr(m.status),
    payout: safeInt(m.payout),
    risk: safeFloat(m.risk),
    vector: safeStr(m.vector),
  };
}

export function normalizeEvidence(raw: Record<string, unknown> | null | undefined): EvidenceDTO {
  if (!raw) return emptyEvidence();
  const m = applyMap(raw, EVIDENCE_MAP);
  return {
    id: safeInt(m.id),
    verdictId: safeInt(m.verdictId),
    findingId: safeInt(m.findingId),
    requestUrl: safeStr(m.requestUrl),
    responseStatus: safeInt(m.responseStatus),
    consistent: safeBool(m.consistent),
  };
}

export function normalizeOverview(raw: Record<string, unknown> | null | undefined): OverviewDTO {
  if (!raw) return emptyOverview();
  const m = applyMap(raw, OVERVIEW_MAP);
  return {
    targets: safeInt(m.targets),
    endpoints: safeInt(m.endpoints),
    findings: safeInt(m.findings),
    confirmed: safeInt(m.confirmed),
    activeScans: safeInt(m.activeScans),
    highSignal: safeInt(m.highSignal),
    avgRisk: safeFloat(m.avgRisk),
    riskDistribution: (m.riskDistribution as Record<string, number>) ?? {},
    severity: (m.severity as Record<string, number>) ?? {},
    pipeline: (m.pipeline as Record<string, number>) ?? {},
    vectorDistribution: (m.vectorDistribution as Record<string, number>) ?? {},
    topTargets: safeArr<Record<string, unknown>>(m.topTargets).map(t => normalizeTarget(t)),
  };
}

export function normalizePaginated<T>(
  raw: Record<string, unknown>,
  itemNormalizer: (item: Record<string, unknown>) => T,
): PaginatedDTO<T> {
  const items = safeArr<Record<string, unknown>>(raw.items).map(itemNormalizer);
  const metaRaw = raw.meta as Record<string, number> | undefined;
  return {
    items,
    meta: {
      total: safeInt(metaRaw?.total ?? raw.total, items.length),
      skip: safeInt(metaRaw?.skip ?? raw.skip, 0),
      limit: safeInt(metaRaw?.limit ?? raw.limit, 100),
    },
  };
}

// ── Fetch helpers ───────────────────────────────────────────────────

async function fetchRaw<T>(path: string): Promise<T> {
  const token = sessionStorage.getItem('rastro-token');
  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`/api${path}`, { headers });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
}

// ── Public API adapter functions ────────────────────────────────────

export async function fetchTargets(skip = 0, limit = 100): Promise<PaginatedDTO<TargetDTO>> {
  const raw = await fetchRaw<Record<string, unknown>>(`/targets?skip=${skip}&limit=${limit}`);
  return normalizePaginated(raw, normalizeTarget);
}

export async function fetchOpportunities(skip = 0, limit = 100): Promise<PaginatedDTO<OpportunityDTO>> {
  const raw = await fetchRaw<Record<string, unknown>>(`/opportunities?skip=${skip}&limit=${limit}`);
  return normalizePaginated(raw, normalizeOpportunity);
}

export async function fetchEndpoints(targetId?: number, skip = 0, limit = 100): Promise<PaginatedDTO<EndpointDTO>> {
  const params = new URLSearchParams({ skip: String(skip), limit: String(limit) });
  if (targetId) params.set('target_id', String(targetId));
  const raw = await fetchRaw<Record<string, unknown>>(`/endpoints?${params}`);
  return normalizePaginated(raw, normalizeEndpoint);
}

export async function fetchFindings(targetId?: number, skip = 0, limit = 100): Promise<PaginatedDTO<FindingDTO>> {
  const params = new URLSearchParams({ skip: String(skip), limit: String(limit) });
  if (targetId) params.set('target_id', String(targetId));
  const raw = await fetchRaw<Record<string, unknown>>(`/findings?${params}`);
  return normalizePaginated(raw, normalizeFinding);
}

export async function fetchEvidence(verdictId?: number, skip = 0, limit = 100): Promise<PaginatedDTO<EvidenceDTO>> {
  const params = new URLSearchParams({ skip: String(skip), limit: String(limit) });
  if (verdictId) params.set('verdict_id', String(verdictId));
  const raw = await fetchRaw<Record<string, unknown>>(`/evidence?${params}`);
  return normalizePaginated(raw, normalizeEvidence);
}

export async function fetchOverview(): Promise<OverviewDTO> {
  const raw = await fetchRaw<Record<string, unknown>>('/overview');
  return normalizeOverview(raw);
}

// ── Empty DTO factories (guarantee no undefined/null) ──────────────

export function emptyTarget(): TargetDTO {
  return { id: 0, name: '', domain: '', payout: 0, score: 0, risk: 0, roi: 0, endpoints: 0, findings: 0, confirmedFindings: 0, competition: 0, freshness: 0 };
}

export function emptyOpportunity(): OpportunityDTO {
  return { id: 0, targetId: 0, name: '', domain: '', payout: 0, score: 0, risk: 0, roi: 0, endpoints: 0, findings: 0, competition: 0, freshness: 0, surfaces: [], vectors: [] };
}

export function emptyEndpoint(): EndpointDTO {
  return { id: 0, targetId: 0, path: '', method: 'GET', risk: 0, confidence: 0, vector: '', labels: [], signals: [], attackSurface: [], actionable: false };
}

export function emptyFinding(): FindingDTO {
  return { id: 0, targetId: 0, endpointId: 0, title: '', severity: 'info', confidence: 0, status: 'open', payout: 0, risk: 0, vector: '' };
}

export function emptyEvidence(): EvidenceDTO {
  return { id: 0, verdictId: 0, findingId: 0, requestUrl: '', responseStatus: 0, consistent: false };
}

export function emptyOverview(): OverviewDTO {
  return { targets: 0, endpoints: 0, findings: 0, confirmed: 0, activeScans: 0, highSignal: 0, avgRisk: 0, riskDistribution: {}, severity: {}, pipeline: {}, vectorDistribution: {}, topTargets: [] };
}

// ── Progressive Hydration ──────────────────────────────────────────────
//
// Loading strategy:
//   1. cached data (instant)
//   2. fast summary/mobile endpoint (low latency)
//   3. full detail fetch (on demand)
//
// Every consumer gets data immediately, then it gets progressively richer.

type FetchFn<T> = () => Promise<T>;

export async function withProgressiveHydration<T>(
  key: string,
  fetchFull: FetchFn<T>,
  fetchSummary?: FetchFn<T>,
): Promise<{ data: T; source: 'cache' | 'summary' | 'full'; stale: boolean }> {
  // Try to load from cache
  const { cacheGet, cacheSet } = await import('../offline/cache');

  const cached = await cacheGet<T>(key);
  if (cached) {
    if (!cached.stale) {
      return { data: cached.data, source: 'cache', stale: false };
    }
    // Stale cache: show it while fetching fresh data
    if (fetchSummary) {
      fetchSummary()
        .then((fresh) => cacheSet(key, fresh))
        .catch(() => {});
      return { data: cached.data, source: 'cache', stale: true };
    }
  }

  // No cache: try summary endpoint first (fast path)
  if (fetchSummary) {
    try {
      const summary = await fetchSummary();
      await cacheSet(key, summary);
      return { data: summary, source: 'summary', stale: false };
    } catch {
      // fall through to full fetch
    }
  }

  // Full fetch
  const full = await fetchFull();
  await cacheSet(key, full);
  return { data: full, source: 'full', stale: false };
}

export async function fetchMobileSummary(): Promise<Record<string, unknown>> {
  return fetchRaw('/mobile/summary');
}

export async function fetchMobileDashboard(): Promise<Record<string, unknown>> {
  return fetchRaw('/mobile/dashboard');
}

export async function getOrchestratorHighlights(): Promise<Array<{ action_id: string; label: string; route?: string }>> {
  try {
    const resp = await fetchRaw<{ decisions: Array<{ action: string; label: string; payload: { route?: string } }> }>('/orchestrator/highlights');
    return (resp.decisions ?? []).map(d => ({
      action_id: d.action,
      label: d.label,
      route: d.payload?.route,
    }));
  } catch {
    return [];
  }
}
