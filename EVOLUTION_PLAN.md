# Rastro Evolution Plan — Multi-Device Unified System

**Version:** 1.1 (draft)
**Status:** Planning
**Target:** Production-ready multi-device investigation OS

---

## 1. Vision

Transform Rastro from a single-user local-first desktop app into a **multi-device synchronized platform** where:

- PC, mobile, and web show the same real-time state
- Backend is the single source of truth
- Actions on one device propagate to all others
- Notifications reach you everywhere
- UI adapts to device context

---

## 2. Architecture Overview

```
┌────────────────────────────────────────────────────┐
│                   PostgreSQL DB                      │
│  (single source of truth, replaces SQLite primary)  │
└──────────┬─────────────────────────────────────────┘
           │
┌──────────▼──────────────────────────────────────────┐
│              FastAPI Backend                         │
│  Auth │ REST │ WebSocket │ SSE │ Notifications      │
└──┬───────────────┬──────────────┬──────────────────┘
   │               │              │
   ▼               ▼              ▼
┌──────┐    ┌──────────┐   ┌──────────┐
│Desktop│    │  Mobile   │   │   Web    │
│pywebview│   │ Capacitor │   │  Browser │
│Win/Linux│   │  Android  │   │  (Vite)  │
└────────┘   └──────────┘   └──────────┘
```

---

## 3. Milestones & Phases

### Phase 1: Foundation (Week 1-2)
**Goal: PostgreSQL + auth + user management**

| Task | Details | Files affected | Dependencies |
|------|---------|----------------|-------------|
| 1.1 | Database migration: SQLite → PostgreSQL | `database/db.py`, `database/models.py` | — |
| 1.2 | User model + Email/password auth | `database/models.py`, new `api/routers/auth_users.py` | 1.1 |
| 1.3 | JWT + refresh tokens | `core_engines/auth/` | 1.2 |
| 1.4 | Session management (multi-device) | `core_engines/auth/`, new `core_engines/session/` | 1.3 |
| 1.5 | Update all DB session handlers for async | `api/routers/*`, `api/services/*` | 1.1 |
| 1.6 | Migrate seed data to PostgreSQL | `database/seed.py` | 1.1 |

### Phase 2: Real-time Sync (Week 3-4)
**Goal: WebSocket + SSE layer for live updates**

| Task | Details | Files affected | Dependencies |
|------|---------|----------------|-------------|
| 2.1 | WebSocket manager | New `api/ws/manager.py` | Phase 1 |
| 2.2 | Connection auth handshake | `api/ws/auth.py` | 1.3 |
| 2.3 | Event bus → WebSocket bridge | `core_engines/events/` | 2.1 |
| 2.4 | SSE fallback for restricted networks | New `api/routers/sse.py` | 2.1 |
| 2.5 | Client-side WebSocket hook | `frontend/src/lib/ws.ts` | 2.1 |
| 2.6 | Live dashboard updates | `frontend/src/pages/MissionControl.tsx` | 2.5 |

### Phase 3: Notifications (Week 5)
**Goal: Unified notification system**

| Task | Details | Files affected | Dependencies |
|------|---------|----------------|-------------|
| 3.1 | Notification model + CRUD | `database/models.py`, `api/routers/notifications.py` | Phase 1 |
| 3.2 | Desktop notifications (plyer/dbus) | `desktop/notifications.py` | — |
| 3.3 | Firebase Cloud Messaging setup | New `core_engines/push/fcm.py` | 3.1 |
| 3.4 | Email notifications (SMTP) | New `core_engines/push/email.py` | 3.1 |
| 3.5 | In-app notification center UI | `frontend/src/components/` | 3.1 |
| 3.6 | Push preference management | `api/routers/user_prefs.py` | 3.1 |

### Phase 4: Mobile Companion (Week 6-8)
**Goal: Android APK via Capacitor**

| Task | Details | Files affected | Dependencies |
|------|---------|----------------|-------------|
| 4.1 | Capacitor project init | `capacitor.config.ts`, `android/` | — |
| 4.2 | Responsive UI refactor | `frontend/src/components/layout/` | — |
| 4.3 | Mobile navigation + bottom bar | `frontend/src/components/layout/MobileNav.tsx` | 4.2 |
| 4.4 | Touch/gesture optimization | `frontend/src/` | 4.2 |
| 4.5 | APK build + signing | `android/` | 4.1 |
| 4.6 | iOS structure (no build required) | `ios/` | 4.1 |

### Phase 5: Polish + Release (Week 9-10)
**Goal: Production-ready multi-device release**

| Task | Details | Files affected | Dependencies |
|------|---------|----------------|-------------|
| 5.1 | End-to-end sync testing | — | All phases |
| 5.2 | Performance optimization | — | All phases |
| 5.3 | Security audit | — | All phases |
| 5.4 | Documentation update | `README.md`, `ARCHITECTURE.md` | All phases |
| 5.5 | CI/CD for mobile | `.github/workflows/` | Phase 4 |
| 5.6 | v2.0.0 release | — | All phases |

---

## 4. Key Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Database** | PostgreSQL (async via asyncpg) | Multi-device sync, concurrent writes, production-grade |
| **Sync protocol** | WebSocket primary + SSE fallback | Low latency, bidirectional; SSE for restrictive networks |
| **Auth** | bcrypt + JWT + refresh tokens | Industry standard, stateless auth |
| **Notifications** | Desktop (plyer) + FCM + Email + In-app | Cover all device types |
| **Mobile** | Capacitor (not React Native) | Reuses existing React codebase, lighter integration |
| **State management** | Backend as source of truth; Zustand as cache | Eliminates sync conflicts |
| **Desktop packaging** | PyInstaller (existing) + NSIS | No change needed |

---

## 5. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| SQLite → PostgreSQL migration breaks queries | High | Dual DB support during transition; integration tests |
| WebSocket auth race conditions | Medium | Connection auth handshake at ws open time |
| FCM setup complexity | Medium | Start with polling + SSE fallback first |
| Mobile UI feels cramped | High | Incremental responsive refactor; user testing |
| Build pipeline complexity | Medium | CI/CD per platform; reusable build scripts |
| Scope creep | High | Strict phase gating; no new features during migration |

---

## 6. Dependencies to Add

| Package | Purpose | Phase |
|---------|---------|-------|
| `asyncpg` or `psycopg3` | PostgreSQL async driver | 1 |
| `bcrypt` or `passlib[bcrypt]` | Password hashing | 1 |
| `python-jose` or `PyJWT` | JWT tokens | 1 |
| `websockets` | WebSocket protocol | 2 |
| `firebase-admin` | FCM push notifications | 3 |
| `aiosmtplib` | Async email sending | 3 |
| `@capacitor/core` | Mobile bridge | 4 |
| `@capacitor/android` | Android platform | 4 |

---

## 7. Backward Compatibility

- **Existing SQLite database**: Script to migrate SQLite → PostgreSQL
- **Existing API endpoints**: 100% backward compatible (no breaking changes)
- **Frontend state**: Zustand store becomes cache layer; backend remains source of truth
- **Desktop boot**: Unchanged (13-step sequence preserved)
- **Middleware chain**: Unchanged (CORS → RateLimit → Auth)
- **Pipeline core**: UNTOUCHED (Recon → Scoring → Graph → Evidence → Verdict → Report)

---

## 8. Effort Estimate

| Phase | Tasks | Estimated time |
|-------|-------|----------------|
| Phase 1: Foundation | 6 tasks | 2 weeks |
| Phase 2: Real-time sync | 6 tasks | 2 weeks |
| Phase 3: Notifications | 6 tasks | 1 week |
| Phase 4: Mobile Companion | 6 tasks | 3 weeks |
| Phase 5: Polish + Release | 6 tasks | 2 weeks |
| **Total** | **30 tasks** | **10 weeks** |

---

## 9. Getting Started (when approved)

1. Install PostgreSQL: `apt install postgresql` (Linux) or download from postgresql.org
2. Add asyncpg/bcrypt to `requirements.txt`
3. Create `database/migrate_to_pg.py` script
4. Add user model + auth router
5. Update all DB sessions in routers for async

---

*This plan is a living document — update as implementation reveals new constraints.*
