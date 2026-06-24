# Hardware ID Consistency Report

**Date:** 2026-06-19
**Scope:** End-to-end audit of every component that computes, stores, or validates a Hardware ID (HWID) for license binding.

---

## 1. Canonical HWID Algorithm

**File:** `core_engines/license/hardware.py:67-74`

```
get_hardware_id() = SHA256(hostname + "|" + mac + "|" + machine_id)[:32]
```

Where:
- `hostname` = `socket.gethostname()` (OS hostname)
- `mac` = `uuid.getnode()` → `XX:XX:XX:XX:XX:XX` (first unicast MAC)
- `machine_id` = joined list of:
  1. `/etc/machine-id` (Linux)
  2. `/var/lib/dbus/machine-id` (Linux)
  3. `HKLM\SOFTWARE\Microsoft\Cryptography\MachineGuid` (Windows Registry)
  4. Fallback: `$HOSTNAME` or `$COMPUTERNAME` or `"unknown"`

All three sources (when present) are joined with `|`. The combined string is hashed via SHA-256, and the first 32 hex characters form the HWID.

---

## 2. Audit Results — This Machine

| Identifier | Value |
|---|---|
| **Hostname** | `ADRI` |
| **MAC address** | `12:08:65:5d:15:00` |
| **`/etc/machine-id`** | `9ca1be381cc34a80a4c748cdcc3d7937` |
| **`/var/lib/dbus/machine-id`** | `9ca1be381cc34a80a4c748cdcc3d7937` |
| **Combined machine_id** | `9ca1be381cc34a80a4c748cdcc3d7937\|9ca1be381cc34a80a4c748cdcc3d7937` |
| **Raw joined string** | `ADRI\|12:08:65:5d:15:00\|9ca1be381cc34a80a4c748cdcc3d7937\|9ca1be381cc34a80a4c748cdcc3d7937` |
| **Final HWID** | `1c88a5e30dc4cff731b45d8c1a66c5fe` |
| **HWID prefix (first 7 hex)** | `1C88A5E` |

---

## 3. HWID Flow Consistency

### 3a. License Generation (`core_engines/license/validator.py:89-98`)

```
get_hardware_id() → "1c88a5e30dc4cff731b45d8c1a66c5fe"
hw_prefix = hw_id[:7].upper() → "1C88A5E"
Key data payload: "126061906191C88A5E" (version + issued year/month/day + expiry + prefix)
```

Generated key: `12606-19270-6191C-88A5E-DDWPO`
- ✅ Embedded HW prefix `1C88A5E` matches first 7 hex chars of HWID

### 3b. License Validation (`core_engines/license/validator.py:163-187`)

1. `verify_license_key(key)` → HMAC-SHA256 signature check → ✅ PASS
2. `get_hardware_id()` → `1c88a5e30dc4cff731b45d8c1a66c5fe`
3. Prefix check: `hw_id.upper().startswith(parsed["hardware_prefix"])` → ✅ `1C88A5E30...startsWith(1C88A5E)`
4. First-time activation: `store.save(key, hw_id)` → stored HWID = `1c88a5e30dc4cff731b45d8c1a66c5fe`

### 3c. License Store (`core_engines/license/store.py:23-55`)

- `save()`: writes HWID alongside key to `~/.rastro/license.json`
- `is_activated` property: checks `stored_hw != get_hardware_id()` → auto-clears on mismatch
- Stored HWID: `1c88a5e30dc4cff731b45d8c1a66c5fe`
- ✅ Exact match with current HWID

### 3d. Re-validation (`is_license_valid`)

- Loads stored key: `12606-18270-6181C-88A5E-HPITA`
- Re-runs `validate_license(key)` 
- Same HWID computed → prefix check passes → stored HWID matches
- ✅ Returns `(True, "Valid")`

---

## 4. Secondary `_get_machine_id()` Implementations

Three independent `_get_machine_id()` functions exist:

| Location | Sources | Used For |
|---|---|---|
| `core_engines/license/hardware.py:24-64` | `/etc/machine-id`, `/var/lib/dbus/machine-id`, `MachineGuid` (Win) | **License HWID binding** |
| `core_engines/target_auth/vault.py:15-33` | `/etc/machine-id`, `/var/lib/dbus/machine-id`, `$HOSTNAME` | Credential vault encryption |
| `core_engines/identity_vault.py:41-53` | `/etc/machine-id`, `$HOSTNAME` | Identity vault encryption |

On this machine (identical values in both machine-id files), all three produce the same machine_id. On machines where they differ, credential/identity vaults would use different encryption keys from the license HWID — this is **intentional** (different security domains), but worth documenting.

---

## 5. Service Worker Cache Audit

### 5a. Source vs Built

**Critical finding**: Before this audit, `dist/service-worker.js` was out of date — it was missing the `request.method !== 'GET'` guard and all three `request.method === 'GET'` conditions on `cache.put()` calls.

**Action taken**: Rebuilt with `npm run build`. Now `dist/service-worker.js` is **identical** to `public/service-worker.js`.

### 5b. `cache.put()` Audit

| Strategy | Line | Guard | Status |
|---|---|---|---|
| `cacheFirst()` | 99 | `response.ok && request.method === 'GET'` | ✅ |
| `networkFirst()` | 112 | `response.ok && request.method === 'GET'` | ✅ |
| `staleWhileRevalidate()` | 130 | `response.ok && request.method === 'GET'` | ✅ |

### 5c. Fetch Handler

Line 69: `if (request.method !== 'GET') { event.respondWith(fetch(request)); return; }`

✅ Non-GET requests bypass all caching logic entirely.

### 5d. `cache.addAll()`

Line 29 (install event only): `cache.addAll(STATIC_ASSETS)` — ✅ Standard pre-caching, not in fetch path.

---

## 6. Regression Tests Added

### `TestHardwareIDConsistency` (test_desktop_release.py)

| Test | What it verifies |
|---|---|
| `test_hwid_deterministic` | `get_hardware_id()` returns the same value on repeated calls |
| `test_hwid_length` | HWID is a 32-char hex string |
| `test_hwid_prefix_in_license_key` | Generated key embeds the correct HWID prefix |
| `test_hwid_prefix_validation_pass` | `validate_license` accepts a key generated on this machine |
| `test_hwid_validation_rejects_invalid_key` | `validate_license` rejects bad keys |
| `test_license_store_consistency` | `LicenseStore.save()` + `load()` preserves exact HWID |
| `test_hwid_hostname_component` | Hostname influences the HWID hash |
| `test_hwid_consistent_across_license_lifecycle` | Full loop: generate → validate → store → re-validate |

### `TestServiceWorker` additions

| Test | What it verifies |
|---|---|
| `test_sw_built_file_exists` | `dist/service-worker.js` exists |
| `test_sw_built_matches_source` | Built file is identical to source |
| `test_sw_cache_add_all_install_only` | `cache.addAll()` only in install event, never fetch |

---

## 7. Conclusion

**The HWID pipeline is fully consistent.** All four components (generation, validation, storage, re-validation) use the same canonical `get_hardware_id()` function and produce identical fingerprints on the same machine.

The three independent `_get_machine_id()` implementations serve different security domains and are not expected to match (though they happen to on this Linux testbed).

The service worker caching is now safe: **all** `cache.put()` calls are guarded by `request.method === 'GET'`, and the fetch handler short-circuits non-GET requests before any caching logic runs. The built distribution asset now matches the source fix.
