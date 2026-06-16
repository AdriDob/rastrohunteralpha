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
  request_body: string | null;
  response_body: string | null;
  request_headers: string | null;
  response_headers: string | null;
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

// --- New types for Mission Control 2.0 ---

export interface SystemHealth {
  status: string;
  uptime_hint: string;
  database: {
    targets: number;
    endpoints: number;
    findings: number;
    verdicts: number;
    intel_programs: number;
  };
  pipeline: {
    confirmed_verdicts: number;
    active_scans: number;
  };
  last_activity: {
    last_scan: string | null;
    last_finding: string | null;
  };
}

export interface OverviewData {
  target_count: number;
  endpoint_count: number;
  finding_count: number;
  confirmed_verdicts: number;
  active_scans: number;
  high_signal_endpoints: number;
  avg_risk_score: number;
  risk_distribution: Record<string, number>;
  vector_distribution: Record<string, number>;
  severity_counts: Record<string, number>;
  pipeline_stages: Record<string, number>;
  top_targets: TopTarget[];
}

export interface TopTarget {
  id: number;
  name: string;
  domain: string | null;
  endpoint_count: number;
  priority: number;
  roi_score: number;
  quality: number;
  complexity_score: number;
  attack_surface_score: number;
}

export interface QuickWin {
  endpoint_path: string;
  endpoint_method: string;
  quick_win_score: number;
  roi_score: number;
  confidence_score: number;
  exploitability_score: number;
  complexity_score: number;
  category: string;
  reasoning: string;
  supporting_signals: string[];
  estimated_payout: number;
  estimated_effort_minutes: number;
  verdict_status: string | null;
  verdict_confidence: number | null;
  evidence_count: number;
  reproducibility_score: number | null;
}

export interface ImmediateAction {
  path: string;
  method: string;
  action: string;
  priority: string;
  confidence: number;
  risk_score: number;
  reason: string;
  steps: string[];
}

export interface QuickWinsReport {
  generated_at: string;
  target_name: string;
  top_quick_wins: QuickWin[];
  fast_exploit_paths: {
    entry_endpoint: string;
    entry_method: string;
    chain_length: number;
    vulnerability_type: string;
    payout_likelihood: number;
    evidence_steps: string[];
    impact_summary: string;
    path_id: string;
  }[];
  low_effort_high_roi_targets: {
    target_name: string;
    endpoint_path: string;
    endpoint_method: string;
    roi_score: number;
    complexity_score: number;
    effort_estimate_minutes: number;
    reason: string;
    is_partially_confirmed: boolean;
    is_underexplored: boolean;
  }[];
  immediate_action_endpoints: ImmediateAction[];
  confidence_ranked_opportunities: QuickWin[];
  total_opportunities: number;
  avg_quick_win_score: number;
  exploitability_score: number;
  fastest_path_minutes: number;
  total_estimated_value: number;
}

export interface AssistantInsight {
  id: string;
  type: string;
  title: string;
  description: string;
  severity: string;
  timestamp: string;
  source: string;
}

export interface TargetSummary {
  id: number;
  name: string;
  opportunities: number;
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
  [key: string]: unknown;
}

export interface AssistantSummary {
  summary: string;
  top_insight: string;
  investigation_summary: string;
  highest_priority_risk: string;
  suggested_human_action: string;
  status: string;
  top_target?: TargetSummary;
}

export interface AssistantContext {
  targets: number;
  findings: number;
  active_hypotheses: number;
  recent_activity: string;
  system_status: string;
}

export interface AssistantRecommendation {
  action: string;
  type: string;
  priority: string;
  reason: string;
  target_id?: number;
  target_name?: string;
  endpoint?: string;
}

export interface AssistantNextAction {
  recommended_action: string;
  action_type: string;
  reasoning: string;
  priority: string;
  context: string;
  route?: string;
  url?: string;
  label?: string;
  description?: string;
}

export interface TimelineEvent {
  event_type: string;
  timestamp: string;
  source: string;
  description: string;
  target_id: number | null;
  target_name: string | null;
  endpoint_id: number | null;
  endpoint_path: string | null;
  verdict_id: number | null;
  verdict_status: string | null;
  finding_id: number | null;
  report_title: string | null;
  confidence: number | null;
  duration_ms: number | null;
  metadata: Record<string, unknown>;
}

export interface TimelineData {
  events: TimelineEvent[];
  total_events: number;
  generated_at: string;
}

export interface ReplayTarget {
  id: number;
  name: string;
  domain: string | null;
  created_at: string | null;
}

export interface ReplayFrame {
  stage: string;
  timestamp: string;
  data: Record<string, unknown>;
  summary: string;
}

export interface ReplayData {
  target_id: number;
  target_name: string;
  domain: string | null;
  generated_at: string;
  timeline: ReplayFrame[];
  endpoints: Record<string, unknown>[];
  hot_paths: Record<string, unknown>[];
  evidence: Record<string, unknown>[];
  verdicts: Record<string, unknown>[];
  findings: Record<string, unknown>[];
  reports: Record<string, unknown>[];
  screenshots: Record<string, unknown>[];
  quick_wins: Record<string, unknown>[];
  ai_explanations: Record<string, unknown>[];
  memory_records: Record<string, unknown>[];
  total_frames: number;
}

export interface ConfidenceFactor {
  name: string;
  value: number;
  weight: number;
  contribution: number;
  description: string;
}

export interface ConfidenceAudit {
  item_id: string;
  item_type: string;
  item_label: string;
  overall_score: number;
  factors: ConfidenceFactor[];
  historical_influence: number;
  evidence_influence: number;
  roi_influence: number;
  reasoning_summary: string;
  audited_at: string;
}

export interface ConfidenceReport {
  audits: ConfidenceAudit[];
  average_confidence: number;
  total_audited: number;
  generated_at: string;
}

export interface ReviewItem {
  item_id: string;
  item_type: string;
  label: string;
  tier: string;
  confidence_score: number;
  reason: string;
  factors: Record<string, unknown>[];
  target_id: number | null;
  target_name: string | null;
  created_at: string | null;
}

export interface ReviewQueue {
  high_confidence: ReviewItem[];
  medium_confidence: ReviewItem[];
  low_confidence: ReviewItem[];
  total_items: number;
  counts: { high: number; medium: number; low: number };
  generated_at: string;
}

export interface IntelligenceHistory {
  summary: string;
  total_targets: number;
  total_endpoints: number;
  total_findings: number;
  total_patterns: number;
  generated_at: string;
  [key: string]: unknown;
}

export interface IntelligenceTrends {
  trends: {
    name: string;
    direction: string;
    magnitude: number;
    description: string;
  }[];
  generated_at: string;
  [key: string]: unknown;
}

export interface IntelligenceRecommendations {
  targets: { target_id: number; name: string; reason: string; priority: number }[];
  surfaces: { surface: string; reason: string; priority: number }[];
  quick_wins: { endpoint: string; reason: string; priority: number }[];
  reports: { title: string; reason: string; priority: number }[];
  generated_at: string;
  [key: string]: unknown;
}

export interface IntelligenceState {
  last_analysis: string | null;
  last_snapshot_daily: string | null;
  total_patterns_learned: number;
  total_recommendations_generated: number;
  total_snapshots_created: number;
  total_analysis_time_ms: number;
}

export interface DiffFinding {
  title: string;
  category: string;
  description: string;
  affected_objects: string;
  confidence: number;
  supporting_signals: string[];
  risk_level: string;
  requires_validation: boolean;
  novelty_score: number;
  confidence_score: number;
  potential_roi: number;
  validation_priority: number;
}

export interface DifferentialData {
  target_differences: DiffFinding[];
  endpoint_differences: DiffFinding[];
  historical_changes: DiffFinding[];
  cross_target_patterns: DiffFinding[];
  web3_differences: DiffFinding[];
  interesting_anomalies: DiffFinding[];
  confidence: number;
  summary: string;
}

export interface VisualBlock {
  type: string;
  content: string;
  highlight_level: string;
}

export interface ScreenshotAnnotation {
  category: string;
  detail: string;
  severity: string;
}

export interface ScreenshotSpec {
  title: string;
  target: string;
  endpoint: string;
  vulnerability_type: string;
  severity: string;
  roi_score: number;
  visual_blocks: VisualBlock[];
  annotations: ScreenshotAnnotation[];
  before_state: string;
  after_state: string;
  attack_path_summary: string;
  confidence: number;
}

export interface ScreenshotBundle {
  specs: ScreenshotSpec[];
  summary: string;
  key_risks: string[];
  roi_highlights: string[];
}

export interface ActivityEvent {
  type: string;
  id: number;
  title?: string;
  severity?: string;
  status?: string;
  hot_path_id?: string;
  confidence?: number;
  mode?: string;
  endpoint_count?: number;
  attempt?: string;
  url?: string;
  timestamp: string;
  target_id?: number;
}

export interface ActivityFeed {
  events: ActivityEvent[];
  total: number;
}

export interface DigestData {
  high_signal_findings: number;
  total_endpoints_scanned: number;
  pending_review: number;
  new_opportunities: number;
  summary: string;
  [key: string]: unknown;
}

// ─── Operations Layer types ──────────────────────────────────────────

export interface MorningBrief {
  generated_at: string;
  period: string;
  new_targets: number;
  new_endpoints: number;
  new_evidence: number;
  quick_wins_count: number;
  pending_findings: number;
  highest_roi_opportunity: { id: number; name: string; roi: number } | null;
  summary: string;
}

export interface EveningSummary {
  generated_at: string;
  period: string;
  scans_executed: number;
  endpoints_discovered: number;
  evidence_generated: number;
  verdicts_created: number;
  reports_produced: number;
  adaptive_learning_updates: number;
  total_events: number;
  summary: string;
}

export interface TimelineEventOp {
  type: string;
  id: number;
  label: string;
  severity?: string;
  status?: string;
  confidence?: number;
  mode?: string;
  endpoint_count?: number;
  attempt?: string;
  url?: string;
  notification_type?: string;
  target_id?: number;
  timestamp: string;
}

export interface UnifiedTimeline {
  events: TimelineEventOp[];
  total: number;
  since: string;
}

export interface FavoriteItem {
  id: number;
  item_type: string;
  item_id: number;
  label: string | null;
  created_at: string;
}

export interface FavoriteList {
  items: FavoriteItem[];
}

export interface TaskItem {
  id: number;
  title: string;
  description: string | null;
  status: string;
  priority: string;
  linked_type: string | null;
  linked_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface TaskList {
  items: TaskItem[];
}

export interface SessionData {
  id: number | null;
  name: string;
  current_target_id: number | null;
  current_investigation: Record<string, unknown> | null;
  open_evidence_ids: number[];
  current_replay_id: number | null;
  current_report_draft: Record<string, unknown> | null;
  updated_at: string;
}

export interface OperationalMetrics {
  generated_at: string;
  total_verdicts: number;
  confirmed_verdicts: number;
  total_findings: number;
  total_evidence: number;
  evidence_growth_7d: number;
  findings_growth_7d: number;
  confidence_distribution: Record<string, number>;
  average_investigation_time_minutes: number;
  average_report_creation_time_minutes: number;
  quick_win_conversion_rate: number;
}

export interface SelfTestResult {
  component: string;
  status: string;
  detail: string;
}

export interface SelfTestReport {
  generated_at: string;
  overall_status: string;
  all_ok: boolean;
  components: SelfTestResult[];
  summary: string;
}

export interface NotificationItem {
  id: number;
  type: string;
  message: string;
  linked_type: string | null;
  linked_id: number | null;
  is_read: boolean;
  created_at: string;
}

export interface NotificationList {
  items: NotificationItem[];
}

// ─── Opportunity Intelligence types ──────────────────────────────────

export interface EVHData {
  value: number;
  rating: 'high' | 'medium' | 'low';
  estimated_payout: number;
  success_probability: number;
  estimated_effort_hours: number;
  explanation: string;
}

export interface ScoreBreakdown {
  reward_score: number;
  reward_explanation: string;
  competition_score: number;
  competition_explanation: string;
  discovery_score: number;
  discovery_explanation: string;
  execution_score: number;
  execution_explanation: string;
  intelligence_score: number;
  intelligence_explanation: string;
  strategic_score: number;
  strategic_explanation: string;
  confidence_score: number;
  confidence_explanation: string;
}

export interface OpportunityItem {
  id: string;
  name: string;
  category: string;
  subcategory: string;
  priority: string;
  score: number;
  source_type: string;
  source_name: string;
  public_url: string;
  scope_summary: string;
  reward_info: string;
  technology_tags: string[];
  confidence: number;
  reasoning: string[];
  created_at: string;
  last_update: string;
  has_rewards: boolean;
  estimated_payout: number;
  estimated_effort_hours: number;
  evh: EVHData | null;
  score_breakdown: ScoreBreakdown | null;
}

export interface OpportunityOverview {
  metrics: {
    opportunities_total: number;
    providers_active: number;
    average_score: number;
    average_evh_top10: number;
    by_priority: Record<string, number>;
    by_category: Record<string, number>;
    evh_distribution: { high: number; medium: number; low: number; average_evh: number };
    providers_health: Record<string, string>;
  };
  providers: { name: string; category: string; opportunity_count: number; health_status: string; last_refresh: string | null }[];
  recommendations_summary: string;
  last_refresh: string;
}

export interface OpportunityRecommendations {
  top_opportunities: OpportunityItem[];
  top_independent: OpportunityItem[];
  top_web3: OpportunityItem[];
  fast_roi: OpportunityItem[];
  long_term: OpportunityItem[];
  low_competition: OpportunityItem[];
  evh_ranked: OpportunityItem[];
  summary: string;
  generated_at: string;
}

export interface OpportunityHistoryEntry {
  id: string;
  timestamp: string;
  period: string;
  opportunity_count: number;
  metrics: Record<string, unknown>;
}

export interface OpportunityHistory {
  snapshots: OpportunityHistoryEntry[];
  trends: Record<string, unknown>;
  count: number;
}

export interface EVHRanking {
  rankings: OpportunityItem[];
  summary: { high: number; medium: number; low: number; average_evh: number };
  count: number;
}

export interface IdentityAccount {
  provider_name: string;
  email: string;
  session_state: string;
  last_checked: string | null;
  health_status: string;
  has_credentials: boolean;
}

export interface IdentityAccounts {
  accounts: IdentityAccount[];
  connected_count: number;
}

export interface CategoryInfo {
  name: string;
  count: number;
}

export interface OpportunityCategories {
  categories: CategoryInfo[];
  total: number;
}

// ─── Contract DTOs (camelCase, normalized) ──────────────────────────
// These are the canonical frontend DTOs. All raw backend data must
// pass through the adapter layer before reaching UI components.

export interface TargetDTO {
  id: number;
  name: string;
  domain: string;
  payout: number;
  score: number;
  risk: number;
  roi: number;
  endpoints: number;
  findings: number;
  confirmedFindings: number;
  competition: number;
  freshness: number;
}

export interface OpportunityDTO {
  id: number;
  targetId: number;
  name: string;
  domain: string;
  payout: number;
  score: number;
  risk: number;
  roi: number;
  endpoints: number;
  findings: number;
  competition: number;
  freshness: number;
  surfaces: string[];
  vectors: string[];
}

export interface EndpointDTO {
  id: number;
  targetId: number;
  path: string;
  method: string;
  risk: number;
  confidence: number;
  vector: string;
  labels: string[];
  signals: string[];
  attackSurface: string[];
  actionable: boolean;
}

export interface FindingDTO {
  id: number;
  targetId: number;
  endpointId: number;
  title: string;
  severity: string;
  confidence: number;
  status: string;
  payout: number;
  risk: number;
  vector: string;
}

export interface EvidenceDTO {
  id: number;
  verdictId: number;
  findingId: number;
  requestUrl: string;
  responseStatus: number;
  consistent: boolean;
  requestBody?: string;
  responseBody?: string;
  requestHeaders?: string;
  responseHeaders?: string;
}

export interface OverviewDTO {
  targets: number;
  endpoints: number;
  findings: number;
  confirmed: number;
  activeScans: number;
  highSignal: number;
  avgRisk: number;
  riskDistribution: Record<string, number>;
  severity: Record<string, number>;
  pipeline: Record<string, number>;
  vectorDistribution: Record<string, number>;
  topTargets: TargetDTO[];
}

export interface PaginatedDTO<T> {
  items: T[];
  meta: {
    total: number;
    skip: number;
    limit: number;
  };
}

// ─── Accessibility Layer types ──────────────────────────────────────

export interface KeyboardShortcut {
  key: string;
  description: string;
  category: string;
}

// ─── Execution Layer types ──────────────────────────────────────────

export interface ExecutionRecord {
  action_id: string;
  action_type: string;
  label: string;
  status: string;
  duration_ms: number;
  user_id?: string;
  payload: Record<string, unknown>;
  result: Record<string, unknown>;
  error?: string;
  outcome_score: number;
  timestamp: number;
}

export interface ExecutionStats {
  total_executions: number;
  by_type: Record<string, {
    count: number;
    avg_score: number;
    avg_duration: number;
    errors: number;
  }>;
  recent: ExecutionRecord[];
}

export interface ScorecardData {
  latest: {
    period_start: number;
    period_end: number;
    total_actions: number;
    success_rate: number;
    avg_outcome_score: number;
    total_value_delivered: number;
    by_type: Record<string, {
      count: number;
      avg_score: number;
      avg_duration: number;
      errors: number;
    }>;
    system_health: string;
    active_decisions: number;
    memory_usage: number;
  };
  trend: {
    trend: string;
    delta: number;
    start_rate: number;
    current_rate: number;
  };
  history: Record<string, unknown>[];
}

export interface ExplanationData {
  id: string;
  decision_id: string;
  action: string;
  summary: string;
  reasoning_chain: string[];
  confidence: number;
  source: string;
  input_signals: { type: string }[];
  alternatives: string[];
  outcome?: string;
  timestamp: number;
}

export interface DecisionTraceData {
  trace_id: string;
  decision_id: string;
  action: string;
  steps: {
    name: string;
    input: unknown;
    output: unknown;
    duration_ms: number;
    metadata: Record<string, unknown>;
  }[];
  context: Record<string, unknown>;
  outcome?: string;
  started_at: number;
  completed_at?: number;
  total_duration_ms: number;
}

export interface OutcomeSummary {
  total: number;
  success_rate: number;
  by_type: Record<string, {
    count: number;
    successes: number;
    total_value: number;
    success_rate: number;
    avg_value: number;
  }>;
}

export interface DecisionMemoryEntry {
  id: number;
  key: string;
  details?: {
    id: string;
    action: string;
    reason: string;
    confidence: number;
    source: string;
    outcome?: string;
    timestamp: number;
  };
  created_at: string;
}

export interface InsightArchiveEntry {
  id: number;
  key: string;
  details?: {
    id: string;
    title: string;
    description: string;
    insight_type: string;
    source: string;
    severity: string;
    tags: string[];
    timestamp?: number;
  };
  created_at: string;
}

export interface ActionDTO {
  id: string;
  label: string;
  action_type: string;
  route?: string;
  payload: Record<string, unknown>;
  requires_confirmation: boolean;
}

export interface InvestigationState {
  target: { id: number; name: string; domain: string | null };
  coverage: {
    total_endpoints: number;
    scored: number;
    actionable: number;
    high_risk: number;
    total_findings: number;
  };
  verdicts: {
    total: number;
    confirmed: number;
    rejected: number;
    inconclusive: number;
    confidence_avg: number;
  };
  findings_by_severity: Record<string, number>;
  interpretation: {
    narrative: string;
    focus: string;
    phase: string;
    risk_level: string;
  };
}

export interface ReportNarrative {
  hot_path_id: string;
  status: string;
  title: string;
  severity: string;
  cvss: string;
  affected_endpoint: string;
  attack_vector: string;
  narrative: string;
  reproduction_steps: string[];
  remediation: string;
  poc_curl: string;
  bounty_estimate: string;
  evidence_count: number;
  export_formats_available: string[];
  target_name: string;
}

export interface ReportNarrativeResult {
  target: { id: number; name: string; domain: string | null };
  program: { name: string; platform: string; bounty_range: string };
  narratives: ReportNarrative[];
  total_confirmed: number;
  narratives_generated: number;
}

export interface AttackPathExplanation {
  hot_path_id: string;
  path_type: string;
  description: string;
  path_value: string;
  risk_context: {
    high_risk_endpoints: number;
    actionable_endpoints: number;
    total_relevant_endpoints: number;
    confirmed_verdicts_on_path: number;
  };
  involved_targets: { id: number; name: string }[];
  attack_surfaces: { surface: string; count: number }[];
  explanation: string;
  recommended_action: {
    action: string;
    priority: string;
    estimated_effort: string;
  };
}

export interface UnifiedReasoning {
  target: { id: number; name: string; domain: string | null };
  web2_analysis: {
    endpoint_count: number;
    high_risk: number;
    actionable: number;
    top_vectors: { vector: string; count: number }[];
    top_signals: { signal: string; count: number }[];
  };
  web3_analysis: {
    endpoint_count: number;
    high_risk: number;
    actionable: number;
    findings: number;
    verdicts: number;
    top_vectors: { vector: string; count: number }[];
    top_signals: { signal: string; count: number }[];
  };
  unified_narrative: string;
  attack_surface_merge: { surface: string; count: number; domain: string }[];
}

export interface BountyPotential {
  target: { id: number; name: string; domain: string | null };
  signals: {
    total_endpoints: number;
    critical_endpoints: number;
    idor_candidates: number;
    actionable_endpoints: number;
    confirmed_findings: number;
    total_findings: number;
    findings_by_severity: Record<string, number>;
    target_quality: number;
    complexity: number;
  };
  payout_estimate: {
    conservative_usd: number;
    moderate_usd: number;
    optimistic_usd: number;
    currency: string;
    confidence: string;
  };
  factors: {
    signal_quality: string;
    surface_complexity: string;
    has_confirmed_findings: boolean;
    has_critical_surface: boolean;
    research_maturity: string;
  };
  explanation: string;
  recommended_focus: string;
}

export interface DailyBriefing {
  generated_at: string;
  period: string;
  system_state: {
    targets: number;
    total_endpoints: number;
    high_signal_endpoints: number;
    actionable_endpoints: number;
    total_findings: number;
    total_verdicts: number;
  };
  recent_activity: {
    new_endpoints_24h: number;
    new_findings_24h: number;
    new_verdicts_24h: number;
  };
  top_surfaces: { surface: string; count: number }[];
  priority_targets: {
    id: number;
    name: string;
    domain: string | null;
    endpoints: number;
    high_risk: number;
    actionable: number;
    findings: number;
    confirmed: number;
    verdicts: number;
  }[];
  summary: string;
}

export interface SystemIntelligenceReport {
  generated_at: string;
  scope: string;
  coverage: {
    total_targets: number;
    total_endpoints: number;
    total_findings: number;
    total_verdicts: number;
    total_actionable: number;
    total_high_risk: number;
    total_confirmed_verdicts: number;
    targets_with_coverage: number;
    targets_with_findings: number;
  };
  bounty_potential: {
    conservative_usd: number;
    moderate_usd: number;
    currency: string;
  };
  top_targets: {
    target_id: number;
    name: string;
    domain: string | null;
    endpoints: number;
    high_risk_endpoints: number;
    actionable_endpoints: number;
    findings: number;
    confirmed_verdicts: number;
    top_surface: string;
    roi_score: number;
    quality_score: number;
    priority_score: number;
    complexity_score: number;
  }[];
  recommended_priority: {
    focus: string;
    target_name?: string;
    target_id?: number;
    reason: string;
  };
}

// ── Report types ──

export interface ReportItem {
  id: number;
  format: string;
  summary: string;
  severity: string;
  finding_ids: number[];
  created_at: string | null;
}

export interface ReportFull {
  id: number;
  investigation_id: number | null;
  format: string;
  content: Record<string, unknown> | null;
  finding_ids: number[];
  created_at: string | null;
}

// ── IDOR result types ──

export interface IDORResultItem {
  parameter: string;
  original_value: string;
  probe_value: string;
  baseline_status: number;
  probe_status: number;
  body_diff_ratio: number;
  sensitive_fields_leaked: string[];
  verdict: string;
  reason: string;
}

export interface IDORScanResponse {
  total_tests: number;
  vulnerable: IDORResultItem[];
  blocked: IDORResultItem[];
  inconclusive: IDORResultItem[];
  elapsed_ms: number;
  summary: string;
}

// ── Validation result types ──

export interface VerdictDetail {
  id: number;
  status: string;
  confidence: number;
  label: string;
  risk_score: number;
  summary: string | null;
  curl_command: string | null;
  detection_engine: string | null;
}

export interface ValidationResult {
  verdict: VerdictDetail;
  evidence: Evidence[];
  validated: boolean;
  report?: Record<string, unknown>;
  report_error?: string;
}

// ── Phase 0: Identity & Investigation types ──

export interface TargetIdentity {
  id: number;
  target_id: number;
  label: string;
  auth_type: string;
  is_baseline: boolean;
  is_active: boolean;
  session_valid: boolean;
  session_expires_at: string | null;
  created_at: string | null;
}

export interface TargetIdentityCreate {
  label: string;
  auth_type: string;
  username?: string;
  password?: string;
  token?: string;
  api_key?: string;
  cookies?: Record<string, string>;
  login_url?: string;
  login_params?: Record<string, unknown>;
  is_baseline?: boolean;
}

export interface TargetSessionStatus {
  identity_id: number;
  is_valid: boolean;
  expires_at: string | null;
  last_refresh_at: string | null;
  failure_count: number;
}

export interface Investigation {
  id: number;
  target_id: number;
  target_name: string;
  name: string;
  status: string;
  pipeline_state: Record<string, unknown>;
  notes: string | null;
  tags: string[];
  created_at: string | null;
  updated_at: string | null;
}

export interface ValidationRun {
  id: number;
  investigation_id: number | null;
  endpoint_id: number;
  identity_baseline_id: number | null;
  identity_probe_id: number | null;
  status: string;
  verdict_id: number | null;
  started_at: string | null;
  finished_at: string | null;
}

// ── Investigation types ──

export interface InvestigationCreatePayload {
  target_id: number;
  name: string;
  notes?: string;
  tags?: string[];
}

export interface InvestigationUpdatePayload {
  name?: string;
  status?: string;
  notes?: string;
  tags?: string[];
  pipeline_state?: Record<string, unknown>;
}

export interface PipelineTimelineEvent {
  stage: string;
  status: string;
  label: string;
  timestamp: string | null;
}

export interface InvestigationDashboard {
  investigation: Investigation;
  stats: {
    endpoints: number;
    findings: number;
    findings_by_severity: Record<string, number>;
    verdicts: number;
    confirmed_verdicts: number;
  };
  pipeline: {
    stages: Record<string, number>;
    timeline: PipelineTimelineEvent[];
    overall_confidence: number;
    progress_pct: number;
  };
}

// ── Report types ──

