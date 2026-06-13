import type {
  PaginatedResult, PaginationFilters,
  SystemHealth, OverviewData,
  QuickWinsReport,
  AssistantInsight, AssistantSummary, AssistantContext,
  AssistantRecommendation, AssistantNextAction,
  TimelineData, ReplayTarget, ReplayData,
  ConfidenceReport, ReviewQueue,
  IntelligenceHistory, IntelligenceTrends,
  IntelligenceRecommendations, IntelligenceState,
  DifferentialData,
  ScreenshotBundle,
  ActivityFeed, DigestData,
  InvestigationState, ReportNarrativeResult,
  AttackPathExplanation, UnifiedReasoning,
  BountyPotential, DailyBriefing as AssistantDailyBriefing, SystemIntelligenceReport,
} from '../types';

const BASE = '/api';

function getAuthHeaders(): Record<string, string> {
  const token = sessionStorage.getItem('rastro-token');
  return token ? { 'Authorization': `Bearer ${token}` } : {};
}

export async function fetchJson<T>(path: string, opts?: RequestInit): Promise<T> {
  const headers = { ...getAuthHeaders(), ...(opts?.headers || {}) } as Record<string, string>;
  const res = await fetch(`${BASE}${path}`, { ...opts, headers });

  if (res.status === 401) {
    sessionStorage.removeItem('rastro-token');
    window.location.href = '/';
    throw new Error('Session expired');
  }

  if (res.status === 403) {
    window.location.href = '/activate';
    throw new Error('License required');
  }

  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
}

export function setAuthToken(token: string | null) {
  if (token) {
    sessionStorage.setItem('rastro-token', token);
  } else {
    sessionStorage.removeItem('rastro-token');
  }
}

export function getAuthToken(): string | null {
  return sessionStorage.getItem('rastro-token');
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

// --- System & Overview ---
export function getSystemHealth() {
  return fetchJson<SystemHealth>('/system/health');
}

export function getOverview() {
  return fetchJson<OverviewData>('/overview');
}

// --- Quick Wins ---
export function evaluateQuickWins(targetId?: number) {
  const body = targetId ? { target_id: targetId } : {};
  return fetchJson<{ report: QuickWinsReport; snapshot_status: string }>('/quick-wins/evaluate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

// --- AI Assistant ---
export function getAssistantInsights() {
  return fetchJson<{ insights: AssistantInsight[]; count: number }>('/assistant/insights');
}

export function getAssistantTopInsight() {
  return fetchJson<AssistantInsight>('/assistant/insights/top');
}

export function getAssistantSummary() {
  return fetchJson<AssistantSummary>('/assistant/summary');
}

export function getAssistantContext() {
  return fetchJson<AssistantContext>('/assistant/context');
}

export function getAssistantRecommendations() {
  return fetchJson<{ recommendations: AssistantRecommendation[] }>('/assistant/recommendations');
}

export function getAssistantNextAction() {
  return fetchJson<AssistantNextAction>('/assistant/recommendations/best');
}

export function getInvestigationState(targetId: number) {
  return fetchJson<InvestigationState>(`/assistant/investigation/${targetId}`);
}

export function getReportNarrative(targetId: number) {
  return fetchJson<ReportNarrativeResult>(`/assistant/narrative/${targetId}`);
}

export function getAttackPathExplanation(hotPathId: string) {
  return fetchJson<AttackPathExplanation>(`/assistant/attack-path/${encodeURIComponent(hotPathId)}`);
}

export function getUnifiedReasoning(targetId: number) {
  return fetchJson<UnifiedReasoning>(`/assistant/unified/${targetId}`);
}

export function getBountyPotential(targetId: number) {
  return fetchJson<BountyPotential>(`/assistant/bounty/${targetId}`);
}

export function getAssistantDailyBriefing() {
  return fetchJson<AssistantDailyBriefing>('/assistant/briefing');
}

export function getSystemIntelligenceReport() {
  return fetchJson<SystemIntelligenceReport>('/assistant/intelligence-report');
}

// --- Timeline ---
export function getTimeline(targetId?: number, limit?: number, eventType?: string) {
  const p = new URLSearchParams();
  if (targetId) p.set('target_id', String(targetId));
  if (limit) p.set('limit', String(limit));
  if (eventType) p.set('event_type', eventType);
  const q = p.toString() ? `?${p}` : '';
  return fetchJson<TimelineData>(`/system/timeline${q}`);
}

// --- Replay ---
export function getReplayTargets() {
  return fetchJson<{ targets: ReplayTarget[]; total: number }>('/system/replay');
}

export function getReplay(targetId: number) {
  return fetchJson<ReplayData>(`/system/replay/${targetId}`);
}

// --- Confidence ---
export function getConfidenceAudit(itemType?: string, limit?: number) {
  const p = new URLSearchParams();
  if (itemType) p.set('item_type', itemType);
  if (limit) p.set('limit', String(limit));
  const q = p.toString() ? `?${p}` : '';
  return fetchJson<ConfidenceReport>(`/system/confidence${q}`);
}

// --- Review Queue ---
export function getReviewQueue(limit?: number) {
  const p = limit ? `?limit=${limit}` : '';
  return fetchJson<ReviewQueue>(`/system/review${p}`);
}

// --- Intelligence ---
export function getIntelligenceHistory() {
  return fetchJson<IntelligenceHistory>('/intelligence/history');
}

export function getIntelligenceTrends() {
  return fetchJson<IntelligenceTrends>('/intelligence/trends');
}

export function getIntelligenceRecommendations() {
  return fetchJson<IntelligenceRecommendations>('/intelligence/recommendations');
}

export function getIntelligenceState() {
  return fetchJson<IntelligenceState>('/intelligence/state');
}

// --- Differential Intelligence ---
export function getDifferentialAnalysis(targetId?: number) {
  const p = targetId ? `?target_id=${targetId}` : '';
  return fetchJson<DifferentialData>(`/differential-intelligence/analyze${p}`);
}

// --- Screenshots ---
export function getScreenshots(targetId?: number) {
  const p = targetId ? `?target_id=${targetId}` : '';
  return fetchJson<ScreenshotBundle>(`/screenshots${p}`);
}

// --- Activity ---
export function getActivity(limit?: number, hours?: number) {
  const p = new URLSearchParams();
  if (limit) p.set('limit', String(limit));
  if (hours) p.set('hours', String(hours));
  const q = p.toString() ? `?${p}` : '';
  return fetchJson<ActivityFeed>(`/activity${q}`);
}

// --- Digest ---
export function getDigest() {
  return fetchJson<DigestData>('/digest');
}

// ─── Operations Layer ───────────────────────────────────────────────

export function getMorningBrief() {
  return fetchJson<import('../types').MorningBrief>('/operations/briefing/morning');
}

export function getEveningSummary() {
  return fetchJson<import('../types').EveningSummary>('/operations/briefing/evening');
}

export function getUnifiedTimeline(limit?: number, hours?: number, eventType?: string) {
  const p = new URLSearchParams();
  if (limit) p.set('limit', String(limit));
  if (hours) p.set('hours', String(hours));
  if (eventType) p.set('event_type', eventType);
  return fetchJson<import('../types').UnifiedTimeline>(`/operations/timeline?${p}`);
}

export function getFavorites(itemType?: string) {
  const p = itemType ? `?item_type=${itemType}` : '';
  return fetchJson<import('../types').FavoriteList>(`/operations/favorites${p}`);
}

export function addFavorite(itemType: string, itemId: number, label?: string) {
  return fetchJson<{ id: number; status: string }>('/operations/favorites', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ item_type: itemType, item_id: itemId, label }),
  });
}

export function removeFavorite(favoriteId: number) {
  return fetchJson<{ status: string }>(`/operations/favorites/${favoriteId}`, { method: 'DELETE' });
}

export function getTasks(status?: string, priority?: string) {
  const p = new URLSearchParams();
  if (status) p.set('status', status);
  if (priority) p.set('priority', priority);
  return fetchJson<import('../types').TaskList>(`/operations/tasks?${p}`);
}

export function createTask(title: string, description?: string, status?: string, priority?: string, linkedType?: string, linkedId?: number) {
  return fetchJson<{ id: number; status: string }>('/operations/tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, description, status, priority, linked_type: linkedType, linked_id: linkedId }),
  });
}

export function updateTask(taskId: number, updates: Record<string, unknown>) {
  return fetchJson<{ id: number; status: string }>(`/operations/tasks/${taskId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  });
}

export function deleteTask(taskId: number) {
  return fetchJson<{ status: string }>(`/operations/tasks/${taskId}`, { method: 'DELETE' });
}

export function getSession() {
  return fetchJson<import('../types').SessionData>('/operations/session');
}

export function updateSession(data: Record<string, unknown>) {
  return fetchJson<{ id: number | null; status: string }>('/operations/session', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export function getOperationalMetrics() {
  return fetchJson<import('../types').OperationalMetrics>('/operations/metrics');
}

export function runSelfTest() {
  return fetchJson<import('../types').SelfTestReport>('/operations/self-test', { method: 'POST' });
}

export function getNotifications(unreadOnly?: boolean) {
  const p = unreadOnly ? '?unread_only=true' : '';
  return fetchJson<import('../types').NotificationList>(`/operations/notifications${p}`);
}

export function createNotification(type: string, message: string, linkedType?: string, linkedId?: number) {
  return fetchJson<{ id: number; status: string }>('/operations/notifications', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ notification_type: type, message, linked_type: linkedType, linked_id: linkedId }),
  });
}

export function markNotificationRead(notificationId: number) {
  return fetchJson<{ status: string }>(`/operations/notifications/${notificationId}/read`, { method: 'PATCH' });
}

export function markAllNotificationsRead() {
  return fetchJson<{ status: string }>('/operations/notifications/mark-all-read', { method: 'POST' });
}

// ─── Opportunity Intelligence ───────────────────────────────────────

export function getOpportunityOverview() {
  return fetchJson<import('../types').OpportunityOverview>('/opportunity/overview');
}

export function getOpportunityTop(limit?: number) {
  const p = limit ? `?limit=${limit}` : '';
  return fetchJson<{ opportunities: import('../types').OpportunityItem[]; count: number }>(`/opportunity/top${p}`);
}

export function getOpportunityRecommendations() {
  return fetchJson<import('../types').OpportunityRecommendations>('/opportunity/recommendations');
}

export function getOpportunityEVHRankings(limit?: number) {
  const p = limit ? `?limit=${limit}` : '';
  return fetchJson<import('../types').EVHRanking>(`/opportunity/evh${p}`);
}

export function getOpportunityScoreBreakdown(oppId: string) {
  return fetchJson<import('../types').OpportunityItem>(`/opportunity/score-breakdown/${oppId}`);
}

export function getOpportunityCategories() {
  return fetchJson<import('../types').OpportunityCategories>('/opportunity/categories');
}

export function getOpportunityByCategory(category: string) {
  return fetchJson<{ opportunities: import('../types').OpportunityItem[]; count: number }>(`/opportunity/by-category/${category}`);
}

export function getEmergingOpportunities() {
  return fetchJson<{ opportunities: import('../types').OpportunityItem[]; count: number }>('/opportunity/emerging');
}

export function getIndependentOpportunities() {
  return fetchJson<{ opportunities: import('../types').OpportunityItem[]; count: number }>('/opportunity/independent');
}

export function getWeb3Opportunities() {
  return fetchJson<{ opportunities: import('../types').OpportunityItem[]; count: number }>('/opportunity/web3');
}

export function getOpportunityHistory(period?: string, limit?: number) {
  const p = new URLSearchParams();
  if (period) p.set('period', period);
  if (limit) p.set('limit', String(limit));
  return fetchJson<import('../types').OpportunityHistory>(`/opportunity/history?${p}`);
}

export function refreshOpportunities() {
  return fetchJson<{ status: string; count: number; refreshed_at: string }>('/opportunity/refresh', { method: 'POST' });
}

// ─── Identity Vault ─────────────────────────────────────────────────

export function getIdentityAccounts() {
  return fetchJson<import('../types').IdentityAccounts>('/opportunity/identity/accounts');
}

export function storeIdentity(provider: string, email: string, token?: string, password?: string, metadata?: Record<string, string>) {
  return fetchJson<{ status: string; provider: string; email: string }>('/opportunity/identity/store', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ provider, email, token, password, metadata }),
  });
}

export function removeIdentity(provider: string) {
  return fetchJson<{ status: string; provider: string }>(`/opportunity/identity/remove/${provider}`, { method: 'POST' });
}

export function getIdentityStatus(provider: string) {
  return fetchJson<{ provider: string; account: import('../types').IdentityAccount; session_health: { connected: boolean; reason: string } }>(`/opportunity/identity/status/${provider}`);
}

// ─── Execution Layer ─────────────────────────────────────────────────

export function getExecutionTrackerStats() {
  return fetchJson<import('../types').ExecutionStats>('/execution/tracker');
}

export function getExecutionRecent(limit?: number) {
  const p = limit ? `?limit=${limit}` : '';
  return fetchJson<{ executions: import('../types').ExecutionRecord[] }>(`/execution/tracker/recent${p}`);
}

export function getExecutionScorecard() {
  return fetchJson<import('../types').ScorecardData>('/execution/scorecard');
}

export function getExecutionOutcomes(limit?: number) {
  const p = limit ? `?limit=${limit}` : '';
  return fetchJson<{ recent: import('../types').ExecutionRecord[]; summary: import('../types').OutcomeSummary }>(`/execution/outcomes${p}`);
}

export function getExecutionExplanations(limit?: number) {
  const p = limit ? `?limit=${limit}` : '';
  return fetchJson<{ explanations: import('../types').ExplanationData[]; count: number }>(`/execution/explain${p}`);
}

export function getExecutionExplanation(decisionId: string) {
  return fetchJson<import('../types').ExplanationData>(`/execution/explain/${decisionId}`);
}

export function getExecutionTraces(limit?: number) {
  const p = limit ? `?limit=${limit}` : '';
  return fetchJson<{ traces: import('../types').DecisionTraceData[]; count: number }>(`/execution/traces${p}`);
}

export function getExecutionDecisions(limit?: number) {
  const p = limit ? `?limit=${limit}` : '';
  return fetchJson<{ decisions: import('../types').DecisionMemoryEntry[]; count: number }>(`/execution/decisions${p}`);
}

export function getExecutionInsights(limit?: number) {
  const p = limit ? `?limit=${limit}` : '';
  return fetchJson<{ insights: import('../types').InsightArchiveEntry[]; count: number; by_type: Record<string, number>; by_severity: Record<string, number> }>(`/execution/insights${p}`);
}

export function listActions() {
  return fetchJson<{ actions: import('../types').ActionDTO[]; count: number }>('/execution/actions');
}

export function getActionHistory(limit?: number) {
  const p = limit ? `?limit=${limit}` : '';
  return fetchJson<{ history: import('../types').ExecutionRecord[] }>(`/execution/actions/history${p}`);
}

export function getActionStats() {
  return fetchJson<import('../types').ExecutionStats>('/execution/actions/stats');
}

export interface DailyBriefing {
  opportunities: Array<{ id: number; name: string; category: string; score: number; estimated_payout: number; priority: string }>;
  critical_risk: { id: number; title: string; severity: string; description: string } | null;
  quick_win: { id: number; title: string; category: string; estimated_payout: number; confidence: number } | null;
  recommended_action: { action: string; label: string; reason: string; confidence: number; payload: { route?: string } } | null;
  system_health: { status: string; services_healthy: number; services_total: number };
  assistant_insight: { focus: string; reason: string; system_state: string };
}

export function getDailyBriefing(): Promise<{ briefing: DailyBriefing; cached: boolean }> {
  return fetchJson<any>('/daily/briefing').then(r => {
    const data = 'data' in r ? (r as any).data : r;
    return { briefing: data.briefing, cached: data.cached };
  });
}

export function getDailyMinimal() {
  return fetchJson<any>('/daily/minimal').then(r => {
    const data = 'data' in r ? (r as any).data : r;
    return data;
  });
}
