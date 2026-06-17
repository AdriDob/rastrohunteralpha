# FEATURE MATRIX — Rastro

Matriz completa de features del sistema.  
**Leyenda:** ✅ DONE | 🔄 IN PROGRESS | ⏳ PLANNED | ❌ CANCELLED

---

## Platform Support

| Feature | Estado | Dependencias | Prioridad | Impacto |
|---------|--------|--------------|-----------|---------|
| Windows (PyInstaller) | ✅ DONE | CI/CD | Alta | Distribución principal |
| Linux (PyInstaller) | ✅ DONE | CI/CD | Alta | Distribución secundaria |
| Linux (AppImage) | ✅ DONE | FUSE | Media | Portable Linux |
| macOS | ⏳ PLANNED | CI/CD macOS | Media | Expansión plataforma |
| Android | ✅ DONE | Capacitor 8 | Alta | Multi-dispositivo |
| iOS | ⏳ PLANNED | Capacitor | Media | Multi-dispositivo |
| Web (PWA) | ⏳ PLANNED | Service Worker | Baja | Acceso rápido |

---

## Authentication & Authorization

| Feature | Estado | Dependencias | Prioridad | Impacto |
|---------|--------|--------------|-----------|---------|
| JWT tokens | ✅ DONE | — | Crítica | Seguridad |
| Rate limiting | ✅ DONE | — | Alta | Protección DoS |
| License system | ✅ DONE | — | Crítica | Comercial |
| User registration | ✅ DONE | SQLite/PostgreSQL | Alta | Multi-dispositivo |
| User login | ✅ DONE | User model | Alta | Multi-dispositivo |
| Refresh tokens | ✅ DONE | JWT | Alta | UX |
| Session management | ⏳ PLANNED | Users | Alta | Multi-device |
| Password recovery | ⏳ PLANNED | Email | Media | UX |
| FREE/PRO/ELITE flags | ⏳ PLANNED | License | Alta | Monetización |

---

## Database

| Feature | Estado | Dependencias | Prioridad | Impacto |
|---------|--------|--------------|-----------|---------|
| SQLite | ✅ DONE | — | Crítica | Local-first |
| PostgreSQL support | ✅ DONE | psycopg2 | Alta | Multi-device |
| SQLite→PG migration | ✅ DONE | PostgreSQL | Alta | Upgrade path |
| Alembic migrations | ⏳ PLANNED | PostgreSQL | Media | DB schema mgmt |

---

## Pipeline Core

| Feature | Estado | Dependencias | Prioridad | Impacto |
|---------|--------|--------------|-----------|---------|
| Recon (subfinder/httpx/katana/wayback) | ✅ DONE | Tools | Crítica | Core |
| Unified Scoring | ✅ DONE | — | Crítica | Core |
| Classification | ✅ DONE | — | Crítica | Core |
| Investigation Graph | ✅ DONE | — | Crítica | Core |
| Evidence Loop | ✅ DONE | — | Crítica | Core |
| Verdict Handler | ✅ DONE | — | Crítica | Core |
| Report Engine | ✅ DONE | — | Crítica | Core |
| Pipeline Timeline + Progress | ✅ DONE | — | Alta | Visibilidad |
| Hypothesis → Investigation | ✅ DONE | — | Alta | Flujo |
| Investigation Auto-creation | ✅ DONE | — | Alta | UX |

---

## AI & Intelligence

| Feature | Estado | Dependencias | Prioridad | Impacto |
|---------|--------|--------------|-----------|---------|
| Ollama integration | ✅ DONE | Ollama | Alta | AI local |
| OpenAI integration | ✅ DONE | API key | Alta | AI cloud |
| Investigation Narrator | ✅ DONE | AI | Alta | UX |
| Personal Learning Engine | ✅ DONE | AI + Profile | Alta | Adaptabilidad |
| Memory Builder (context) | ✅ DONE | PLE | Alta | AI relevance |
| Provider abstraction | ⏳ PLANNED | — | Alta | Flexibilidad |
| Model selector UI | ⏳ PLANNED | Providers | Media | UX |
| SSE streaming | ⏳ PLANNED | Providers | Media | UX real-time |
| Provider auto-fallback | ⏳ PLANNED | Providers | Media | Resiliencia |

---

## Frontend

| Feature | Estado | Dependencias | Prioridad | Impacto |
|---------|--------|--------------|-----------|---------|
| 25 pages | ✅ DONE | — | Crítica | UX completa |
| Lazy loading | ✅ DONE | — | Alta | Performance |
| i18n (español default) | ✅ DONE | — | Alta | Internacionalización |
| Auto-detect OS language | ✅ DONE | — | Media | UX |
| Theme system (dark/light) | ✅ DONE | — | Alta | UX |
| framer-motion transitions | ✅ DONE | — | Media | UX Premium |
| Tailwind v4 | ✅ DONE | — | Alta | Estilo |
| Personal Intelligence page | ✅ DONE | PLE API | Alta | Dashboard personal |
| Language selector | ✅ DONE | i18n | Alta | UX |
| Mobile responsive | ✅ DONE | — | Alta | Multi-device |
| Sidebar with submenus | ✅ DONE | — | Alta | UX |
| Dashboard widgets | ⏳ PLANNED | PLE | Media | Personalización |
| Weekly progress charts | ⏳ PLANNED | PLE | Baja | Dashboard |
| Investigation heatmap | ⏳ PLANNED | Events | Baja | Dashboard |

---

## Desktop

| Feature | Estado | Dependencias | Prioridad | Impacto |
|---------|--------|--------------|-----------|---------|
| pywebview window | ✅ DONE | — | Crítica | Desktop native |
| System tray | ✅ DONE | pystray | Alta | Desktop UX |
| Auto-updater | ✅ DONE | GitHub API | Alta | Distribución |
| 13-step boot | ✅ DONE | — | Alta | Startup |
| Notifications (plyer) | ✅ DONE | — | Media | Desktop alerts |
| DesktopSettings | ✅ DONE | — | Media | UX |

---

## Synchronization

| Feature | Estado | Dependencias | Prioridad | Impacto |
|---------|--------|--------------|-----------|---------|
| WebSocket manager | ✅ DONE | FastAPI/WS | Alta | Multi-device |
| Event bus → WS bridge | ✅ DONE | Events | Alta | Sync |
| Client-side WS hook | ✅ DONE | WebSocket | Alta | Frontend |
| SSE fallback | ⏳ PLANNED | WebSocket | Media | Resiliencia |
| Live dashboard updates | ⏳ PLANNED | WS hook | Media | UX |

---

## Notifications

| Feature | Estado | Dependencias | Prioridad | Impacto |
|---------|--------|--------------|-----------|---------|
| Notification hub | ✅ DONE | — | Alta | Sistema base |
| Notification poller | ✅ DONE | — | Alta | Background |
| Desktop notifications | ✅ DONE | plyer | Alta | UX |
| Smart filtering (PLE) | ✅ DONE | PLE | Alta | Reducción ruido |
| Firebase Cloud Messaging | ⏳ PLANNED | Push | Media | Mobile |
| Email notifications | ⏳ PLANNED | SMTP | Media | Offline |
| Notification preferences | ⏳ PLANNED | User prefs | Media | UX |

---

## Monitoring & Observability

| Feature | Estado | Dependencias | Prioridad | Impacto |
|---------|--------|--------------|-----------|---------|
| System state singleton | ✅ DONE | — | Alta | Monitoreo |
| Event bus | ✅ DONE | — | Alta | Comunicación |
| Metrics collector | ✅ DONE | — | Media | Observabilidad |
| System health endpoint | ✅ DONE | — | Alta | Health check |

---

## Career / Commercial

| Feature | Estado | Dependencias | Prioridad | Impacto |
|---------|--------|--------------|-----------|---------|
| License system | ✅ DONE | — | Crítica | Monetización |
| Product behavior rules | ✅ DONE | — | Alta | UX |
| FREE/PRO/ELITE tiers | ⏳ PLANNED | License | Alta | Monetización |
| Payment integration | ⏳ PLANNED | Tiers | Baja | Futuro |

---

## Documentation

| Feature | Estado | Dependencias | Prioridad | Impacto |
|---------|--------|--------------|-----------|---------|
| README.md | ✅ DONE | — | Crítica | Onboarding |
| ARCHITECTURE.md | ✅ DONE | — | Alta | Developer docs |
| ROADMAP.md | ✅ DONE | — | Alta | Planning |
| OPENCODE_PLAN.md | ✅ DONE | — | Crítica | Agent context |
| EVOLUTION_PLAN.md | ✅ DONE | — | Alta | Planning |
| PROJECT_STATUS.md | ✅ DONE | — | Alta | Governance |
| TIMELINE.md | ✅ DONE | — | Media | History |
| FEATURE_MATRIX.md | ✅ DONE | — | Media | Overview |
| TECH_DEBT.md | ✅ DONE | — | Media | Maintenance |
| INSTALL.md | 🔄 IN PROGRESS | — | Alta | User docs |
| PRODUCT.md | ⏳ PLANNED | — | Media | Commercial |
