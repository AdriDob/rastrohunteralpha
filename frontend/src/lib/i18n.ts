import { createContext, useContext } from 'react';

export type Language = 'en' | 'es';

export interface Translations {
  // Mission
  mission_control: string;
  today_mission: string;
  no_active_mission: string;
  explore_opportunities: string;
  score: string;
  estimated_roi: string;
  effort: string;
  confidence: string;
  evh: string;
  score_breakdown: string;
  why_this_mission: string;
  recommended_action: string;

  // Sidebar / Nav
  sidebar_collapse: string;
  sidebar_expand: string;
  recent: string;
  pinned: string;
  nav_mission: string;
  nav_recon: string;
  nav_findings: string;
  nav_analysis: string;
  nav_operations: string;
  nav_intelligence: string;
  daily_briefing: string;
  actions_view: string;
  history_view: string;
  project_dashboard: string;

  // Discovery & Programs
  program_catalog: string;

  // Opportunities
  opportunity_radar: string;
  opportunity_intel: string;
  opportunities: string;
  no_opportunities: string;
  category: string;
  source: string;
  filter: string;
  sort: string;
  all: string;
  high_confidence: string;
  medium_confidence: string;
  low_confidence: string;

  // Assistant
  ai_assistant: string;
  ai_intelligence: string;
  key_insights: string;
  recommendations: string;
  quick_actions: string;
  summary: string;
  no_summary: string;
  recommended_next_action: string;

  // Pages
  reports: string;
  evidence: string;
  hypotheses: string;
  pipeline: string;
  hot_paths: string;
  attack_surface: string;
  differential: string;
  screenshots: string;
  replay: string;
  confidence_dashboard: string;
  operations: string;
  tasks: string;
  target_detail: string;
  finding_detail: string;
  endpoint_detail: string;
  personal_intelligence: string;

  // Evidence
  evidence_center: string;
  replay_center: string;
  screenshot_center: string;
  no_evidence: string;

  // Reports
  report_center: string;
  report_history: string;
  generate_report: string;
  no_reports: string;

  // Settings
  settings: string;
  settings_title: string;
  settings_section_appearance: string;
  settings_section_language: string;
  settings_language_desc: string;
  settings_theme_desc: string;
  theme: string;
  language: string;
  notifications: string;
  about: string;

  // Operations
  operations_dashboard: string;
  task_queue: string;
  investigations: string;

  // Personal Learning
  adaptive_mode: string;
  adaptive_mode_desc: string;
  export_json: string;
  export_md: string;
  reset_profile: string;
  strength_map: string;
  areas_of_expertise: string;
  success_history: string;
  recommendations_title: string;
  recent_activity: string;
  no_learning_data: string;
  no_learning_data_desc: string;
  no_bug_classes: string;
  no_industries: string;
  targets_label: string;
  findings_label: string;
  hours_label: string;
  sessions_label: string;
  confirmed_label: string;
  high_severity_label: string;
  rejected_label: string;
  duplicates_label: string;
  total_roi: string;

  // Placeholders / Common
  loading: string;
  error: string;
  retry: string;
  cancel: string;
  confirm: string;
  search: string;
  no_results: string;
  close: string;
  open: string;

  // Shortcuts
  keyboard_shortcuts: string;
  global_shortcuts: string;
  navigation_shortcuts: string;
  press_shortcut_hint: string;

  // AI Settings
  settings_section_ai: string;
  settings_ai_provider: string;
  settings_ai_provider_desc: string;
  settings_ai_model: string;
  settings_ai_model_desc: string;
  settings_ai_host: string;
  settings_ai_host_desc: string;
  settings_ai_api_key: string;
  settings_ai_api_key_desc: string;
  settings_ai_save: string;
  settings_ai_saved: string;
  settings_ai_error: string;
  settings_ai_available: string;
  settings_ai_unavailable: string;
  settings_ai_active: string;

  // Financial
  financial_center: string;
  total_revenue: string;
  monthly_revenue: string;
  weekly_revenue: string;
  daily_revenue: string;
  pending_rewards: string;
  approved_rewards: string;
  paid_rewards: string;
  expected_revenue: string;
  annual_forecast: string;
  avg_review_time: string;
  avg_payment_time: string;
  roi_by_program: string;
  roi_by_vulnerability: string;
  roi_by_technology: string;
  revenue_trend: string;
  goals: string;
  goal_progress: string;
  goal_remaining: string;
  goal_deadline: string;
  goal_priority: string;
  add_goal: string;
  accept_rate: string;
  reports_submitted: string;
  reports_accepted: string;
  reports_rejected: string;
  reports_paid: string;
  reports_triaged: string;
  reports_need_info: string;
  total_payout: string;

  // Reports
  report_lifecycle: string;
  report_quality: string;
  report_confidence: string;
  report_duplicate_probability: string;
  report_acceptance_probability: string;
  report_expected_payout: string;
  report_submit: string;
  report_approve: string;
  report_reject: string;
  report_revision: string;
  submitted: string;
  triaged: string;
  resolved: string;
  paid: string;
  duplicate: string;
  informative: string;
  not_applicable: string;

  // AI Agents
  agent_center: string;
  agent_research: string;
  agent_validator: string;
  agent_exploit: string;
  agent_documentation: string;
  agent_strategy: string;
  agent_memory: string;
  agent_financial: string;
  agent_coordinator: string;
  agent_status: string;
  agent_confidence: string;
  agent_last_action: string;
  agent_uptime: string;
  agent_events: string;
  agent_live_status: string;
  agent_event_stream: string;
  agent_coordinator_activity: string;
  agent_working: string;
  agent_idle: string;
  agent_error: string;
  agent_offline: string;
  agent_waiting: string;
  agent_capabilities: string;
  agent_retry_policy: string;
  agent_no_events: string;
  agent_active_pipelines: string;
  agent_pipeline_history: string;
  agent_start_pipeline: string;
  agent_tasks_completed: string;
  agent_tasks_failed: string;
  agent_avg_time: string;
  agent_total_time: string;

  // Executive Dashboard
  executive_dashboard: string;
  dashboard_agent_health: string;
  dashboard_pipeline_overview: string;
  dashboard_financial_preview: string;
  dashboard_system_activity: string;
  dashboard_agents_online: string;
  dashboard_active_pipelines: string;
  dashboard_completed_today: string;
  dashboard_total_revenue: string;
  dashboard_pending_revenue: string;
  dashboard_reports_ready: string;
  dashboard_last_24h: string;

  // Global search
  global_search: string;
  global_search_placeholder: string;

  // Pipeline Monitor
  pipeline_monitor: string;
  pipeline_quality_score: string;
  pipeline_transition_history: string;
  pipeline_no_pipelines: string;
  pipeline_state_pending: string;
  pipeline_state_discovery: string;
  pipeline_state_validation: string;
  pipeline_state_evidence: string;
  pipeline_state_ai_review: string;
  pipeline_state_ready: string;
  pipeline_state_submitted: string;
  pipeline_state_triaged: string;
  pipeline_state_paid: string;
  pipeline_state_closed: string;
  pipeline_state_failed: string;
  pipeline_state_cancelled: string;
  pipeline_progress: string;
  pipeline_from_state: string;
  pipeline_to_state: string;
  pipeline_agent: string;
  pipeline_timestamp: string;
  pipeline_retry_count: string;
  pipeline_cancel: string;
  pipeline_delete: string;
  pipeline_start_new: string;
  pipeline_detail: string;

  // Mode system
  mode_title: string;
  mode_description: string;
  mode_manual: string;
  mode_manual_desc: string;
  mode_automatic: string;
  mode_automatic_desc: string;
  mode_caution: string;
  mode_current: string;

  // Platform integration
  platform_title: string;
  platform_description: string;
  platform_enabled: string;
  platform_action: string;
  platform_action_prepare: string;
  platform_action_open: string;
  platform_action_fill: string;
  platform_action_auto: string;
  platform_username: string;
  platform_api_key: string;
  platform_saved: string;
  platform_save_error: string;

  // Identity Center
  identity_center: string;
  identity_title: string;
  identity_platforms: string;
  identity_email: string;
  identity_wallets: string;
  identity_credentials: string;
  identity_connected: string;
  identity_disconnected: string;
  identity_token_valid: string;
  identity_token_invalid: string;
  identity_last_sync: string;
  identity_mode: string;
  identity_mode_manual: string;
  identity_mode_prepare: string;
  identity_mode_automatic: string;
  identity_connect: string;
  identity_disconnect: string;
  identity_remove: string;
  identity_primary_email: string;
  identity_secondary_email: string;
  identity_never_submit: string;
  identity_vault: string;
  identity_usdc: string;
  identity_binance: string;
  identity_takenos: string;
  identity_public_wallet: string;
  identity_save: string;
  identity_saved: string;
  identity_error: string;
  identity_no_accounts: string;

  // Export
  export_title: string;
  export_as_md: string;
  export_as_html: string;
  export_as_pdf: string;
  export_as_txt: string;
  export_copy: string;
  export_copied: string;
  export_draft_save: string;
  export_draft_saved: string;
  export_versions: string;
  export_version_create: string;
  export_version_created: string;
  export_no_versions: string;
}

import en from './i18n-en';
import es_ from './i18n-es';

export function getTranslations(lang: Language): Translations {
  if (lang === 'es') return es_ as Translations;
  return en as Translations;
}

export interface I18nContextValue {
  lang: Language;
  t: Translations;
  setLang: (l: Language) => void;
}

export const I18nContext = createContext<I18nContextValue>({
  lang: 'es',
  t: getTranslations('es'),
  setLang: () => {},
});

export function useI18n(): I18nContextValue {
  return useContext(I18nContext);
}
