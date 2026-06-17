# Real-World Validation Report

**Target:** testphp.vulnweb.com (Acunetix test site — designed for security testing)

**Date:** 2026-06-17 14:36:49 UTC

## Pipeline Results

| Stage | Status | Detail | Time |
|-------|--------|--------|------|
| 1_create_target | ✅ ok | Target #123 created | 0.18s |
| 2_add_endpoints | ✅ ok | 25/25 endpoints created | 2.33s |
| 3_hypotheses | ✅ ok | 15 hypotheses generated | 0.04s |
| 4_investigation | ✅ ok | Investigation #2 created | 0.11s |
| 5_dashboard | ✅ ok | Dashboard loaded | 0.06s |
| 6_report | ✅ ok | Report generated | 0.08s |
| 7_export | ✅ ok | 0 reports available for export | 0.05s |
| 8_scoring | ✅ ok | 15/25 endpoints have risk scores | 0.06s |
| 9_attack_surface | ✅ ok | Attack surface loaded | 0.5s |

## Endpoints Found

Total: 25 endpoints

| Path | Method | Risk Score | Labels |
|------|--------|------------|--------|
| /api/user/1 | GET | 66.0 | api, identity, numeric_identifier |
| /admin/admin.php | POST | 45.0 | admin, sensitive, web |
| /api/admin | GET | 45.0 | admin, api, sensitive |
| /graphql | POST | 45.0 | graphql, web |
| /admin/ | GET | 35.0 | admin, sensitive, web |
| /admin/config.php | GET | 35.0 | admin, sensitive, web |
| /backup/ | GET | 35.0 | export, sensitive, web |
| /wp-admin/ | GET | 35.0 | admin, sensitive, web |
| /api/user | GET | 30.0 | api, identity |
| /login.php | POST | 30.0 | auth, web |

## Errors Found

No critical errors.

## UX Issues

None identified in API testing.

## Improvements for Next Version

No immediate improvements required.

## Stage Details

### 1_create_target

- **Status:** ok
- **Detail:** Target #123 created
- **Time:** 0.18s
- **Data:** `{
  "id": 123,
  "name": "AcunetixTest",
  "domain": "testphp.vulnweb.com"
}`

### 2_add_endpoints

- **Status:** ok
- **Detail:** 25/25 endpoints created
- **Time:** 2.33s

### 3_hypotheses

- **Status:** ok
- **Detail:** 15 hypotheses generated
- **Time:** 0.04s
- **Data:** `{
  "total": 15,
  "by_type": {
    "idor": 1,
    "privilege_escalation": 5,
    "data_exposure": 5,
    "graphql_introspection": 1,
    "auth_bypass": 2,
    "ssrf": 1
  },
  "top_priority": "idor",
  "top_score": 6.79
}`

### 4_investigation

- **Status:** ok
- **Detail:** Investigation #2 created
- **Time:** 0.11s
- **Data:** `{
  "id": 2,
  "name": "idor \u2014 AcunetixTest",
  "status": "active"
}`

### 5_dashboard

- **Status:** ok
- **Detail:** Dashboard loaded
- **Time:** 0.06s
- **Data:** `{
  "pipeline_progress": "40%",
  "confidence": 0.0,
  "stages": {
    "recon": 25,
    "hypotheses": 0,
    "validation": 0,
    "evidence": 0,
    "reported": 0
  },
  "stats": {
    "endpoints": 25,
    "findings": 0,
    "findings_by_severity": {},
    "verdicts": 0,
    "confirmed_verdicts": 0
  }
}`

### 6_report

- **Status:** ok
- **Detail:** Report generated
- **Time:** 0.08s
- **Data:** `{
  "title": "Rastro Bug Bounty Report",
  "findings": 1,
  "estimated_value": 258000,
  "markdown_len": 435
}`

### 7_export

- **Status:** ok
- **Detail:** 0 reports available for export
- **Time:** 0.05s

### 8_scoring

- **Status:** ok
- **Detail:** 15/25 endpoints have risk scores
- **Time:** 0.06s

### 9_attack_surface

- **Status:** ok
- **Detail:** Attack surface loaded
- **Time:** 0.5s
- **Data:** `{
  "clusters": 0,
  "hot_paths": 0
}`

