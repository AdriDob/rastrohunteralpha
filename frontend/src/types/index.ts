export interface Target {
  id: number;
  name: string;
  domain: string | null;
  created_at: string | null;
  endpoint_count: number;
  finding_count: number;
  confirmed_findings: number;
  estimated_payout: number;
  roi: number;
  risk_score: number;
  opportunity_score: number;
  competition_score: number;
  freshness_score: number;
}

export interface TargetSummary {
  id: number;
  name: string;
  domain: string | null;
  endpoint_count: number;
  finding_count: number;
  confirmed_count: number;
  estimated_payout: number;
  roi: number;
  max_risk: number;
  surfaces: string[];
  vectors: string[];
  opportunity_score: number;
  competition_score: number;
  freshness_score: number;
}

export interface Endpoint {
  id: number;
  target_id: number;
  path: string;
  method: string;
  risk_score: number;
  confidence: number;
  vector: string;
  labels: string[];
  signals: string[];
  attack_surface: string[];
  actionable: boolean;
}

export interface Finding {
  id: number;
  target_id: number;
  endpoint_id: number | null;
  title: string;
  severity: string;
  description: string | null;
  payout: number;
  target_name: string;
  endpoint_path: string;
  created_at: string | null;
}

export interface Evidence {
  id: number;
  verdict_id: number;
  endpoint_id: number | null;
  attempt_label: string;
  request_url: string;
  request_method: string;
  response_status: number | null;
  consistent: boolean;
  curl_command: string | null;
  body_diff_ratio: number;
}

export interface Opportunity {
  target_id: number;
  name: string;
  domain: string;
  roi: number;
  max_risk: number;
  endpoint_count: number;
  finding_count: number;
  surfaces: string[];
  vectors: string[];
  estimated_payout: number;
  opportunity_score: number;
  competition_score: number;
  freshness_score: number;
}

export interface PipelineStages {
  detected: Finding[];
  validated: Finding[];
  confirmed: Finding[];
  reported: Finding[];
}

export interface Report {
  title: string;
  summary: string;
  findings: Finding[];
  total_findings: number;
  total_estimated_value: number;
  generated_at: string;
  markdown: string;
}

export type AttackSurfaceMap = Record<string, Endpoint[]>;

export interface PaginatedResult<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

export interface PaginationState {
  pageIndex: number;
  pageSize: number;
}

export interface SortingState {
  id: string;
  desc: boolean;
}

export interface HypothesisScore {
  likelihood: number;
  impact: number;
  exploitability: number;
  confidence: number;
  priority_score: number;
  breakdown: Record<string, number>;
}

export interface Hypothesis {
  id: string;
  vulnerability_type: string;
  target_id: number;
  target_name: string;
  endpoint: Record<string, unknown>;
  likelihood: number;
  impact: number;
  exploitability: number;
  confidence: number;
  priority_score: number;
  roi_score: number;
  evidence: string[];
  reasoning: string;
  suggested_actions: string[];
  source: string;
  vector: string;
  attack_surface_labels: string[];
  similarity_to_past: number;
  past_pattern_id: string | null;
  score: HypothesisScore;
}

export interface HypothesisEngineOutput {
  attack_queue: Hypothesis[];
  total_hypotheses: number;
  by_source: Record<string, number>;
  by_type: Record<string, number>;
  top_priority: Hypothesis | null;
  summary: string;
  total_roi_value: number;
  avg_roi: number;
  max_roi: number;
  profitable_count: number;
}

export interface ROIDetail {
  endpoint_id: number | null;
  hypothesis_id: string | null;
  vulnerability_type: string;
  path: string;
  method: string;
  roi_normalized: number;
  roi_ratio: number;
  payout_estimate: number;
  time_cost_hours: number;
  expected_return: number;
  expected_cost: number;
  probability_success: number;
  priority_score: number;
  is_profitable: boolean;
  breakdown: Record<string, number>;
}

export interface TargetROI {
  target_id: number;
  target_name: string;
  total_hypotheses: number;
  avg_roi: number;
  max_roi: number;
  profitable_count: number;
  total_expected_return: number;
  total_expected_cost: number;
  highest_payout: number;
  top_opportunities: ROIDetail[];
  all_roi: ROIDetail[];
}

export interface PaginationFilters {
  skip?: number;
  limit?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  search?: string;
}
