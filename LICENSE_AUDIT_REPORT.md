# License Audit Report — Rastro v1.5.0

**Date:** 2026-06-19
**Context:** Desktop build shows "Activate your license to continue" screen on first boot

---

## 1. Executive Summary

The activation screen is **expected behavior** for all Rastro builds (including Desktop). It is **not a regression** from recent auth/onboarding changes. The license system was introduced in commit `f7c5a8c` (P4: "License system (HMAC-SHA256, hardware binding, activation UI)").

The Desktop binary has never auto-activated a license. Every installation must either:
- **Enter a license key** via the activation UI (standard path), or
- **Have a license pre-generated** by the licensing server (production), or
- **Generate a dev key** via `generate_license()` (development/testing only)

---

## 2. Where the License Screen Originates

The chain is:

```
Frontend API call (e.g., GET /api/overview)
  → fetchJson() in frontend/src/lib/api.ts
  → Backend AuthMiddleware (api/middleware/auth_middleware.py:59-67)
    → calls is_license_valid() from core_engines/license/validator.py
    → checks ~/.rastro/license.json
    → if no valid license → returns HTTP 403
  → fetchJson() catches 403
    → window.location.href = '/activate' (api.ts:35)
  → React Router renders Activation.tsx at /activate
    → Shows "Activate your license to continue"
```

### Key files:

| File | Role |
|------|------|
| `frontend/src/pages/Activation.tsx` | The activation UI the user sees |
| `frontend/src/lib/api.ts:34-37` | 403 → redirect to `/activate` |
| `api/middleware/auth_middleware.py:59-67` | License check, returns 403 |
| `core_engines/license/validator.py` | `is_license_valid()`, `validate_license()`, `generate_license()` |
| `core_engines/license/store.py` | Persists to `~/.rastro/license.json` |
| `core_engines/license/hardware.py` | Machine fingerprint (MAC + machine-id + hostname) |

---

## 3. License Key Format

```
XXXXX-XXXXX-XXXXX-XXXXX-XXXXX   (25 chars, 5 groups of 5)
```

Encodes:
- Version (1 char)
- Issue date (6 chars: YYMMDD)
- Expiry date (6 chars: YYMMDD)
- Hardware ID prefix (7 chars)
- HMAC-SHA256 signature (5 chars, Base32-encoded)

Validation: HMAC-SHA256 with `RASTRO_LICENSE_SECRET` env var (or default fallback).

---

## 4. Activation Mechanism

The activation flow is:

1. User enters key in the activation form (`Activation.tsx`)
2. Frontend calls `POST /api/license/activate` with `{"key": "XXXXX-..."}` 
3. Backend `validate_license(key)` in `validator.py:163-187`:
   - Parses key fields (version, dates, hardware prefix)
   - Verifies HMAC-SHA256 signature
   - Checks expiry date
   - Checks hardware binding against current machine
   - On success: saves to `~/.rastro/license.json`
4. Frontend redirects to `/` on success

### API endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/license/status` | GET | Returns `{valid, reason, activated}` |
| `/api/license/activate` | POST | Activates with `{"key": "..."}` |
| `/api/license/deactivate` | POST | Clears `~/.rastro/license.json` |

---

## 5. Default/Dev/Demo License

There is **no pre-existing default or demo license baked into the binary**.

However, the source code contains `generate_license(expiry_days=365)` in `core_engines/license/validator.py:89` which generates a valid license for the **current machine**. This function is used by tests and validation scripts but is **not called during Desktop boot**.

The HMAC secret used for signing defaults to:
```python
hashlib.sha256(b"rastro-license-secret-v1").hexdigest()
```
This is **embedded in source code** (`validator.py:27`). It can be overridden with `RASTRO_LICENSE_SECRET` env var.

---

## 6. Files, Environment Variables, and Storage Checked

| Check | Location | Detail |
|-------|----------|--------|
| License file | `~/.rastro/license.json` | `{"license_key": "...", "hardware_id": "...", "activated_at": <ts>}` |
| Env var | `RASTRO_LICENSE_SECRET` | HMAC signing secret (optional, default derived from `b"rastro-license-secret-v1"`) |
| Hardware ID | `get_hardware_id()` | SHA256(hostname + MAC + machine-id) → first 32 hex chars |
| Public paths (no license check) | `auth_middleware.py:12-24` | `/api/health`, `/api/version`, `/api/auth/*`, `/api/license/*`, `/api/docs`, `/api/openapi.json`, `/api/redoc` |

---

## 7. Is This a Regression?

**No.** The license system was introduced in commit `f7c5a8c` (2026-06-13) and has never included auto-activation during Desktop boot. The Desktop binary has **always** required manual license activation since the license system was added. The recent auth/onboarding fixes (`send_auth_header` parameter, `onboarding` kwarg) did not affect the license flow.

`generate_license()` has never been called from `desktop/main_desktop.py` or any `desktop/` module.

---

## 8. Correct Activation Path for This Installation

### Option A: Generate a dev license from Python (recommended for development)

```python
from core_engines.license.validator import generate_license
from core_engines.license import validate_license

key = generate_license(expiry_days=365)
print(f"License key: {key}")
result = validate_license(key)
print(f"Activated: {result}")
```

Or run the existing script:
```bash
python -c "
from core_engines.license.validator import generate_license
from api.main import app
from fastapi.testclient import TestClient
key = generate_license(expiry_days=365)
client = TestClient(app)
r = client.post('/api/license/activate', json={'key': key})
print(r.json())
"
```

### Option B: Manual entry through UI

Run the desktop binary, navigate to the activation screen, and enter a key generated via Option A.

### Option C: Pre-activate before running the binary

```bash
# Activate license via API before launching Desktop
curl -X POST http://127.0.0.1:8000/api/license/activate \
  -H "Content-Type: application/json" \
  -d '{"key": "<generated-key>"}'
```

---

## 9. Design Intent

The license system was designed as a **local-only, source-available** enforcement mechanism:

- **Signed keys** prevent casual tampering (HMAC-SHA256)
- **Hardware binding** ties license to a specific machine
- **No phone-home** — all validation is offline
- **Default secret in source** — the system is not cryptographically strong against a determined attacker; it's a "honesty system" for early access
- **Architecture doc acknowledges**: asymmetric crypto (Ed25519) should replace HMAC in production

The `generate_license()` function comment (`validator.py:92`) explicitly notes:
> "In production, this runs ONLY on the licensing server."

---

## 10. Architecture Diagram

```
┌─────────────────────────────────────────────────┐
│                  Desktop Binary                  │
│  ┌──────────┐    ┌──────────────┐               │
│  │ Frontend │    │  Backend API │               │
│  │ (React)  │◄──►│  (FastAPI)   │               │
│  └────┬─────┘    └──────┬───────┘               │
│       │                  │                       │
│  HTTP 403          AuthMiddleware                │
│  redirect           calls                        │
│  to /activate     is_license_valid()             │
│       │                  │                       │
│       ▼                  ▼                       │
│  ┌──────────┐    ┌──────────────┐               │
│  │Activation│    │core_engines/ │               │
│  │  UI      │    │  license/    │               │
│  │  (enter  │    │  validator   │               │
│  │   key)   │    │  store       │               │
│  └────┬─────┘    │  hardware    │               │
│       │          └──────┬───────┘               │
│       │                 │                       │
│       ▼                 ▼                       │
│  POST /api/        ~/.rastro/                    │
│  license/activate  license.json                  │
└─────────────────────────────────────────────────┘
```

---

## 11. Recommendation

For the current Windows Desktop build under validation: **Generate a development license key using Option A above and enter it in the activation UI.** This is the expected path for development/testing.

For a future production release, a licensing server should issue signed keys using `RASTRO_LICENSE_SECRET` configured as an env var (not the default embedded secret).
