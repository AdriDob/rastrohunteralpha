import type { Translations } from './i18n';

const en: Translations = {
  // Mission
  mission_control: 'Mission Control',
  today_mission: "Today's Mission",
  no_active_mission: 'No active mission.',
  explore_opportunities: 'Explore opportunities or open a target to begin investigating.',
  score: 'Score',
  estimated_roi: 'Est. ROI',
  effort: 'Effort',
  confidence: 'Confidence',
  evh: 'EVH',
  score_breakdown: 'Score Breakdown',
  why_this_mission: 'Why this mission',
  recommended_action: 'Recommended Action',

  // Sidebar / Nav
  sidebar_collapse: 'Collapse sidebar',
  sidebar_expand: 'Expand sidebar',
  recent: 'Recent',
  pinned: 'Pinned',
  nav_mission: 'Mission',
  nav_recon: 'Recon',
  nav_findings: 'Findings',
  nav_analysis: 'Analysis',
  nav_operations: 'Operations',
  nav_intelligence: 'Intelligence',
  daily_briefing: 'Daily Briefing',
  actions_view: 'Actions',
  history_view: 'History',
  project_dashboard: 'Project Dashboard',

  // Discovery & Programs
  program_catalog: 'Program Catalog',

  // Opportunities
  opportunity_radar: 'Opportunity Radar',
  opportunity_intel: 'Opportunity Intelligence',
  opportunities: 'Opportunities',
  no_opportunities: 'No opportunities found.',
  category: 'Category',
  source: 'Source',
  filter: 'Filter',
  sort: 'Sort',
  all: 'All',
  high_confidence: 'High Confidence',
  medium_confidence: 'Medium Confidence',
  low_confidence: 'Low Confidence',

  // Assistant
  ai_assistant: 'AI Assistant',
  ai_intelligence: 'AI Intelligence',
  key_insights: 'Key Insights',
  recommendations: 'Recommendations',
  quick_actions: 'Quick Actions',
  summary: 'Summary',
  no_summary: 'No summary available.',
  recommended_next_action: 'Recommended Next Action',

  // Pages
  reports: 'Reports',
  evidence: 'Evidence',
  hypotheses: 'Hypotheses',
  pipeline: 'Pipeline',
  hot_paths: 'Hot Paths',
  attack_surface: 'Attack Surface',
  differential: 'Differential',
  screenshots: 'Screenshots',
  replay: 'Replay',
  confidence_dashboard: 'Confidence Dashboard',
  operations: 'Operations',
  tasks: 'Tasks',
  target_detail: 'Target Detail',
  finding_detail: 'Finding Detail',
  endpoint_detail: 'Endpoint Detail',
  personal_intelligence: 'Personal Intel',

  // Evidence
  evidence_center: 'Evidence Center',
  replay_center: 'Replay Center',
  screenshot_center: 'Screenshot Center',
  no_evidence: 'No evidence records.',

  // Reports
  report_center: 'Report Center',
  report_history: 'Report History',
  generate_report: 'Generate Report',
  no_reports: 'No reports generated.',

  // Settings
  settings: 'Settings',
  settings_title: 'Settings',
  settings_section_appearance: 'Appearance',
  settings_section_language: 'Language',
  settings_language_desc: 'Choose your preferred language for the interface',
  settings_theme_desc: 'Toggle between dark and light themes',
  theme: 'Theme',
  language: 'Language',
  notifications: 'Notifications',
  about: 'About',

  // Operations
  operations_dashboard: 'Operations Dashboard',
  task_queue: 'Task Queue',
  investigations: 'Investigations',

  // Personal Learning
  adaptive_mode: 'Adaptive Mode',
  adaptive_mode_desc: 'Enable adaptive recommendations based on your profile',
  export_json: 'Export JSON',
  export_md: 'Export MD',
  reset_profile: 'Reset Profile',
  strength_map: 'Strength Map',
  areas_of_expertise: 'Areas of Expertise',
  success_history: 'Success History',
  recommendations_title: 'Recommendations',
  recent_activity: 'Recent Activity',
  no_learning_data: 'No Learning Data Yet',
  no_learning_data_desc: 'Your investigator profile will grow as you investigate targets, create findings, and use the system. Enable Adaptive Mode to start.',
  no_bug_classes: 'No bug class data yet. Create findings to build your strength map.',
  no_industries: 'No industries tracked yet.',
  targets_label: 'Targets',
  findings_label: 'Findings',
  hours_label: 'Hours',
  sessions_label: 'Sessions',
  confirmed_label: 'Confirmed',
  high_severity_label: 'High Severity',
  rejected_label: 'Rejected',
  duplicates_label: 'Duplicates',
  total_roi: 'Total ROI',

  // Placeholders / Common
  loading: 'Loading...',
  error: 'An error occurred.',
  retry: 'Retry',
  cancel: 'Cancel',
  confirm: 'Confirm',
  search: 'Search',
  no_results: 'No results.',
  close: 'Close',
  open: 'Open',

  // Shortcuts
  keyboard_shortcuts: 'Keyboard Shortcuts',
  global_shortcuts: 'Global',
  navigation_shortcuts: 'Navigation',
  press_shortcut_hint: 'Press ⌘/ (Ctrl+/) to open this dialog anytime',

  // AI Settings
  settings_section_ai: 'Artificial Intelligence',
  settings_ai_provider: 'AI Provider',
  settings_ai_provider_desc: 'Select which AI backend to use for analysis and recommendations.',
  settings_ai_model: 'Model',
  settings_ai_model_desc: 'Model to use with this provider.',
  settings_ai_host: 'Host / Base URL',
  settings_ai_host_desc: 'Server address for the AI provider.',
  settings_ai_api_key: 'API Key',
  settings_ai_api_key_desc: 'Leave blank to keep the current key.',
  settings_ai_save: 'Save Config',
  settings_ai_saved: 'Configuration saved.',
  settings_ai_error: 'Failed to save configuration.',
  settings_ai_available: 'Available',
  settings_ai_unavailable: 'Unavailable',
  settings_ai_active: 'Active',
};

export default en;
