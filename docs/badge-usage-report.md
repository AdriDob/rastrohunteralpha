# Badge Usage Audit Report

**Generated:** 2026-06-10  
**Scope:** All files using `variant="success"`, `variant="warning"`, or `variant="error"` on the Badge component.

---

## Canonical Badge Variants

| Variant    | Purpose                          |
|-----------|----------------------------------|
| `default`  | Neutral UI element               |
| `severity` | Risk / intensity scale           |
| `tier`     | Classification levels            |
| `stage`    | Pipeline / lifecycle states      |

## Deprecated Aliases

| Alias      | Canonical Mapping         | Color   |
|-----------|--------------------------|---------|
| `success` | `severity` (low)         | `#22c55e` (green) |
| `warning` | `severity` (medium)      | `#eab308` (amber) |
| `error`   | `severity` (high)        | `#ef4444` (red)   |

---

## Files Using Deprecated Variants

### 1. `src/components/ExecutionPanel.tsx` — **11 total occurrences**

| Line | Code | Variants Used |
|------|------|---------------|
| 40   | `<Badge variant={latest.system_health === 'healthy' ? 'success' : 'warning'}>` | `success`, `warning` |
| 74   | `<Badge variant={exec.outcome_score > 0.7 ? 'success' : exec.outcome_score > 0.3 ? 'warning' : 'error'}>` | `success`, `warning`, `error` |
| 106  | `<Badge variant={exp.confidence > 0.7 ? 'success' : 'warning'}>` | `success`, `warning` |
| 178  | `<Badge variant={det?.outcome === 'success' ? 'success' : det?.outcome === 'error' ? 'error' : 'default'}>` | `success`, `error` |
| 224  | `<Badge variant={det?.severity === 'critical' ? 'error' : det?.severity === 'high' ? 'warning' : 'default'}>` | `error`, `warning` |

#### Per-alias frequency

| Alias    | Count |
|---------|-------|
| success | 4     |
| warning | 4     |
| error   | 3     |

---

## Files NOT Using Deprecated Variants

The following files use only canonical variants (`default`, `severity`, `tier`, `stage`) or the `color` prop directly — no migration needed:

| File | Variants Used |
|------|--------------|
| `src/pages/ActionsView.tsx` | `default` |
| `src/pages/ConfidenceDashboard.tsx` | (none — uses `color` prop) |
| `src/pages/DifferentialEngine.tsx` | `severity`, (none — uses `color`) |
| `src/pages/HistoryView.tsx` | `tier`, `default` |
| `src/pages/InsightsView.tsx` | `tier`, `default` |
| `src/pages/IntelligenceDashboard.tsx` | (none — uses `color` prop) |
| `src/pages/MissionControl.tsx` | `stage`, `severity`, (none — uses `color`) |
| `src/pages/ReplayCenter.tsx` | (none — uses `color` prop) |
| `src/pages/ScreenshotCenter.tsx` | `severity`, (none — uses `color`) |
| `src/pages/TaskQueue.tsx` | (none — custom inline) |
| `src/components/EVHWidget.tsx` | (none — uses `color` prop) |
| `src/components/IdentityVaultWidget.tsx` | (none — uses `color` prop) |

---

## Migration Priority

| Priority | File | Rationale |
|---------|------|-----------|
| **HIGH** | `ExecutionPanel.tsx` | Only file using deprecated aliases. 11 occurrences across 5 lines. Each maps cleanly to `variant="severity"` with a corresponding severity text value. |

---

## Suggested Migration Strategy

Replace deprecated Badge calls with canonical equivalents:

```
Before: <Badge variant="success">{text}</Badge>
After:  <Badge variant="severity">{text}</Badge>

Before: <Badge variant="warning">{text}</Badge>
After:  <Badge variant="severity">{text}</Badge>

Before: <Badge variant="error">{text}</Badge>
After:  <Badge variant="severity">{text}</Badge>
```

**Note:** The canonical `severity` variant resolves color from `severityColors` map based on `text.toLowerCase()`. If the text values (e.g., `system_health`, `outcome_score`) don't match severity keys (`critical`, `high`, `medium`, `low`, `info`), the color will fall back to neutral gray (`#6b7280`). In such cases, use the `color` prop directly or update the text to match severity vocabulary.

---

## Dev Deprecation Warnings

When `import.meta.env.DEV` is `true`, the Badge component emits a `console.warn` once per deprecated variant per session:

```
[Badge] variant="success" is deprecated. Use variant="severity" with the appropriate severity text instead.
[Badge] variant="warning" is deprecated. Use variant="severity" with the appropriate severity text instead.
[Badge] variant="error" is deprecated. Use variant="severity" with the appropriate severity text instead.
```

These warnings are stripped from production builds.
