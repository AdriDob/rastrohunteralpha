import { useQuery } from '@tanstack/react-query';
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
