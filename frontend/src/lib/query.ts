import { useQuery, useMutation } from '@tanstack/react-query';
import * as api from './api';
import type { PaginationFilters } from '../types';

export function useTargets(filters?: PaginationFilters) {
  return useQuery({
    queryKey: ['targets', filters],
    queryFn: () => api.getTargets(filters),
  });
}

export function useTarget(id: number | null) {
  return useQuery({
    queryKey: ['target', id],
    queryFn: () => api.getTarget(id!),
    enabled: id !== null,
  });
}

export function useEndpoints(targetId?: number | null, filters?: PaginationFilters) {
  return useQuery({
    queryKey: ['endpoints', targetId, filters],
    queryFn: () => api.getEndpoints(targetId ?? undefined, filters),
  });
}

export function useEndpoint(id: number | null) {
  return useQuery({
    queryKey: ['endpoint', id],
    queryFn: () => api.getEndpoint(id!),
    enabled: id !== null,
  });
}

export function useFindings(targetId?: number | null, endpointId?: number | null, filters?: PaginationFilters) {
  return useQuery({
    queryKey: ['findings', targetId, endpointId, filters],
    queryFn: () => api.getFindings(targetId ?? undefined, endpointId ?? undefined, filters),
  });
}

export function useEvidence(verdictId?: number | null, filters?: PaginationFilters) {
  return useQuery({
    queryKey: ['evidence', verdictId, filters],
    queryFn: () => api.getEvidence(verdictId ?? undefined, filters),
  });
}

export function useOpportunities(filters?: PaginationFilters) {
  return useQuery({
    queryKey: ['opportunities', filters],
    queryFn: () => api.getOpportunities(filters),
  });
}

export function useAttackSurfaces() {
  return useQuery({ queryKey: ['attackSurfaces'], queryFn: api.getAttackSurfaces });
}

export function usePipeline() {
  return useQuery({ queryKey: ['pipeline'], queryFn: api.getPipeline });
}

export function useRunHypotheses(targetId: number | null) {
  return useQuery({
    queryKey: ['hypotheses', targetId],
    queryFn: () => api.runHypotheses(targetId!),
    enabled: targetId !== null,
    staleTime: Infinity,
    retry: false,
  });
}

export function useTargetROI(targetId: number | null) {
  return useQuery({
    queryKey: ['roi', targetId],
    queryFn: () => api.getTargetROI(targetId!),
    enabled: targetId !== null,
    staleTime: Infinity,
    retry: false,
  });
}

export function useReport() {
  return useQuery({ queryKey: ['report'], queryFn: api.getReport, staleTime: 0 });
}

// --- New hooks ---

export function useSystemHealth() {
  return useQuery({ queryKey: ['systemHealth'], queryFn: api.getSystemHealth, staleTime: 15_000 });
}

export function useOverview() {
  return useQuery({ queryKey: ['overview'], queryFn: api.getOverview, staleTime: 15_000 });
}

export function useQuickWins(targetId?: number) {
  return useQuery({
    queryKey: ['quickWins', targetId],
    queryFn: () => api.evaluateQuickWins(targetId),
    staleTime: 30_000,
  });
}

export function useAssistantInsights() {
  return useQuery({ queryKey: ['assistantInsights'], queryFn: api.getAssistantInsights, staleTime: 30_000 });
}

export function useAssistantTopInsight() {
  return useQuery({ queryKey: ['assistantTopInsight'], queryFn: api.getAssistantTopInsight, staleTime: 30_000 });
}

export function useAssistantSummary() {
  return useQuery({ queryKey: ['assistantSummary'], queryFn: api.getAssistantSummary, staleTime: 30_000 });
}

export function useAssistantContext() {
  return useQuery({ queryKey: ['assistantContext'], queryFn: api.getAssistantContext, staleTime: 30_000 });
}

export function useTimeline(targetId?: number, limit?: number, eventType?: string) {
  return useQuery({
    queryKey: ['timeline', targetId, limit, eventType],
    queryFn: () => api.getTimeline(targetId, limit, eventType),
    staleTime: 15_000,
  });
}

export function useReplayTargets() {
  return useQuery({ queryKey: ['replayTargets'], queryFn: api.getReplayTargets, staleTime: 30_000 });
}

export function useReplay(targetId: number | null) {
  return useQuery({
    queryKey: ['replay', targetId],
    queryFn: () => api.getReplay(targetId!),
    enabled: targetId !== null,
    staleTime: 60_000,
  });
}

export function useConfidenceAudit(itemType?: string, limit?: number) {
  return useQuery({
    queryKey: ['confidenceAudit', itemType, limit],
    queryFn: () => api.getConfidenceAudit(itemType, limit),
    staleTime: 30_000,
  });
}

export function useReviewQueue(limit?: number) {
  return useQuery({
    queryKey: ['reviewQueue', limit],
    queryFn: () => api.getReviewQueue(limit),
    staleTime: 30_000,
  });
}

export function useIntelligenceHistory() {
  return useQuery({ queryKey: ['intelligenceHistory'], queryFn: api.getIntelligenceHistory, staleTime: 60_000 });
}

export function useIntelligenceTrends() {
  return useQuery({ queryKey: ['intelligenceTrends'], queryFn: api.getIntelligenceTrends, staleTime: 60_000 });
}

export function useIntelligenceRecommendations() {
  return useQuery({ queryKey: ['intelligenceRecommendations'], queryFn: api.getIntelligenceRecommendations, staleTime: 60_000 });
}

export function useIntelligenceState() {
  return useQuery({ queryKey: ['intelligenceState'], queryFn: api.getIntelligenceState, staleTime: 60_000 });
}

export function useDifferentialAnalysis(targetId?: number) {
  return useQuery({
    queryKey: ['differentialAnalysis', targetId],
    queryFn: () => api.getDifferentialAnalysis(targetId),
    staleTime: 60_000,
  });
}

export function useScreenshots(targetId?: number) {
  return useQuery({
    queryKey: ['screenshots', targetId],
    queryFn: () => api.getScreenshots(targetId),
    staleTime: 60_000,
  });
}

export function useActivity(limit?: number, hours?: number) {
  return useQuery({
    queryKey: ['activity', limit, hours],
    queryFn: () => api.getActivity(limit, hours),
    staleTime: 15_000,
  });
}

export function useDigest() {
  return useQuery({ queryKey: ['digest'], queryFn: api.getDigest, staleTime: 30_000 });
}

// ── Adapter-based hooks (normalized DTOs) ────────────────────────────

import { fetchOverview, fetchTargets, fetchEndpoints, fetchFindings } from './api/adapter';

export function useOverviewDTO() {
  return useQuery({
    queryKey: ['overviewDTO'],
    queryFn: fetchOverview,
    staleTime: 15_000,
  });
}

export function useTargetsDTO(filters?: PaginationFilters) {
  return useQuery({
    queryKey: ['targetsDTO', filters],
    queryFn: () => fetchTargets(filters?.skip ?? 0, filters?.limit ?? 100),
  });
}

export function useEndpointsDTO(targetId?: number | null, limit = 100) {
  return useQuery({
    queryKey: ['endpointsDTO', targetId, limit],
    queryFn: () => fetchEndpoints(targetId ?? undefined, 0, limit),
  });
}

export function useFindingsDTO(targetId?: number | null, limit = 100) {
  return useQuery({
    queryKey: ['findingsDTO', targetId, limit],
    queryFn: () => fetchFindings(targetId ?? undefined, 0, limit),
  });
}

// ─── Execution Layer hooks ───────────────────────────────────────────

export function useExecutionTrackerStats() {
  return useQuery({
    queryKey: ['execution', 'tracker'],
    queryFn: () => api.getExecutionTrackerStats(),
    refetchInterval: 30_000,
  });
}

export function useExecutionScorecard() {
  return useQuery({
    queryKey: ['execution', 'scorecard'],
    queryFn: () => api.getExecutionScorecard(),
    refetchInterval: 60_000,
  });
}

export function useExecutionExplanations(limit?: number) {
  return useQuery({
    queryKey: ['execution', 'explanations', limit],
    queryFn: () => api.getExecutionExplanations(limit),
    refetchInterval: 60_000,
  });
}

export function useExecutionTraces(limit?: number) {
  return useQuery({
    queryKey: ['execution', 'traces', limit],
    queryFn: () => api.getExecutionTraces(limit),
    refetchInterval: 30_000,
  });
}

export function useExecutionDecisions(limit?: number) {
  return useQuery({
    queryKey: ['execution', 'decisions', limit],
    queryFn: () => api.getExecutionDecisions(limit),
    refetchInterval: 60_000,
  });
}

export function useExecutionInsights(limit?: number) {
  return useQuery({
    queryKey: ['execution', 'insights', limit],
    queryFn: () => api.getExecutionInsights(limit),
    refetchInterval: 60_000,
  });
}

export function useExecutionOutcomes(limit?: number) {
  return useQuery({
    queryKey: ['execution', 'outcomes', limit],
    queryFn: () => api.getExecutionOutcomes(limit),
    refetchInterval: 30_000,
  });
}

export function useActionList() {
  return useQuery({
    queryKey: ['execution', 'actions'],
    queryFn: () => api.listActions(),
  });
}

export function useActionHistory(limit?: number) {
  return useQuery({
    queryKey: ['execution', 'actions', 'history', limit],
    queryFn: () => api.getActionHistory(limit),
    refetchInterval: 30_000,
  });
}

export function useDailyBriefing() {
  return useQuery({
    queryKey: ['daily', 'briefing'],
    queryFn: () => api.getDailyBriefing(),
    staleTime: 30_000,
    refetchInterval: 60_000,
    placeholderData: (prev) => prev,
  });
}

export function useDailyMinimal() {
  return useQuery({
    queryKey: ['daily', 'minimal'],
    queryFn: () => api.getDailyMinimal(),
    staleTime: 15_000,
  });
}

export function useActionStats() {
  return useQuery({
    queryKey: ['execution', 'actions', 'stats'],
    queryFn: () => api.getActionStats(),
    refetchInterval: 60_000,
  });
}

export function useReportsList(limit = 20, offset = 0) {
  return useQuery({
    queryKey: ['reports', limit, offset],
    queryFn: () => api.getReportsList(limit, offset),
  });
}

export function useReportById(id: number | null) {
  return useQuery({
    queryKey: ['report', id],
    queryFn: () => api.getReportById(id!),
    enabled: id !== null,
  });
}

export function useInvestigations(targetId?: number | null, status?: string, limit = 20, offset = 0) {
  return useQuery({
    queryKey: ['investigations', targetId, status, limit, offset],
    queryFn: () => api.getInvestigations(targetId ?? undefined, status, limit, offset),
  });
}

export function useInvestigation(id: number | null) {
  return useQuery({
    queryKey: ['investigation', id],
    queryFn: () => api.getInvestigation(id!),
    enabled: id !== null,
  });
}

export function useInvestigationDashboard(id: number | null) {
  return useQuery({
    queryKey: ['investigationDashboard', id],
    queryFn: () => api.getInvestigationDashboard(id!),
    enabled: id !== null,
    staleTime: 15_000,
  });
}

export function useCreateInvestigation() {
  return useMutation({
    mutationFn: (payload: import('../types').InvestigationCreatePayload) => api.createInvestigation(payload),
  });
}

export function useUpdateInvestigation() {
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: import('../types').InvestigationUpdatePayload }) =>
      api.updateInvestigation(id, payload),
  });
}

export function useDeleteInvestigation() {
  return useMutation({
    mutationFn: (id: number) => api.deleteInvestigation(id),
  });
}

export function useValidateEndpoint() {
  return useMutation({
    mutationFn: (payload: api.ValidateEndpointPayload) => api.validateEndpoint(payload),
  });
}

export function useScanIDOR() {
  return useMutation({
    mutationFn: (payload: api.IDORScanPayload) => api.scanIDOR(payload),
  });
}
