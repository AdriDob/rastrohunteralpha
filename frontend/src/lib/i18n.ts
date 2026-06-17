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
  lang: 'en',
  t: getTranslations('en'),
  setLang: () => {},
});

export function useI18n(): I18nContextValue {
  return useContext(I18nContext);
}
