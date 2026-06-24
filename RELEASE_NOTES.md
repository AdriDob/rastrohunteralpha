# Rastro v1.5.0 Definitive — Release Notes

**Definitive Release** — 2026-06-18

---

## Version

| Campo | Valor |
|-------|-------|
| Versión | `1.5.0` |
| Estado | **Definitive** |
| Tests | **81/81 pasando** (desktop release suite) |
| Frontend | 0 TS errors, ~1.4s build, 551 modules |
| Desktop (Linux) | PyInstaller 6.20.0 bundle (21 MB ELF x86\_64) |
| Desktop (Windows) | PyInstaller bundle (16.8 MB PE32 x86\_64) |
| Android | Capacitor APK debug (4.2 MB) |

---

## Capacidades actuales

### Pipeline de Investigación (Core)
| Etapa | Estado | Descripción |
|-------|--------|-------------|
| Target | ✅ | Creación de objetivos por nombre + dominio |
| Recon | ✅ | subfinder → httpx → katana → waybackurls (manual o scheduler 30min) |
| Scoring | ✅ | 15+ señales heurísticas deterministas, risk\_score por endpoint |
| Attack Surface | ✅ | Clustering, hot path detection, mapa visual |
| Hypothesis | ✅ | Generación automática de hipótesis priorizadas por ROI |
| Investigation | ✅ | Timeline, progreso, auto-creación desde hipótesis |
| Validation | ⚠️ | Replayer + rules + confidence + gate (requiere tokens de sesión) |
| Evidence | ✅ | Evidence graph + store |
| Findings | ✅ | Persistencia con scoring y severidad CVSS v3 |
| Report | ✅ | Export HackerOne JSON, Bugcrowd HTML, Markdown |
| Opportunity Radar | ✅ | 26 oportunidades activas, scoring por layers, paid-first |

### AI Conversacional
| Componente | Estado | Descripción |
|------------|--------|-------------|
| Provider Registry | ✅ | Ollama (local), OpenAI Compatible, fallback rule-based |
| Investigation Narrator | ✅ | 7 funciones: estado, narrativa, attack path, bounty, briefing |
| SSE Streaming | ✅ | Chat stream vía `/api/assistant/chat/stream` |
| Memory | ✅ | Memoria contextual persistente por sesión |

### Desktop
| Característica | Estado |
|----------------|--------|
| PyInstaller bundle | ✅ Linux x86\_64 (21 MB) |
| System tray | ✅ pystray con menú contextual |
| Auto-updater | ✅ GitHub Releases + SHA-256 + rollback |
| Frontend embebido | ✅ Servido desde `_internal/frontend_dist/` |
| run.sh launcher | ✅ Auto-detección de PATH + OLLAMA\_HOST |

### Mobile (Android)
| Característica | Estado |
|----------------|--------|
| Capacitor scaffold | ✅ APK generado con JDK 21 |
| Bottom navigation | ✅ 5 tabs: Dashboard, Investigaciones, Evidencia, Reportes, Ajustes |
| Login funcional | ✅ Conexión a API del desktop |

### Inteligencia
| Módulo | Estado |
|--------|--------|
| Personal Learning Engine (PLE) | ✅ 7 módulos, 12 endpoints, perfil adaptativo |
| Priority Engine | ✅ Layer scoring + dependency graph |
| Insight Archive | ✅ Patrones extraídos + tendencias |
| Diff Intelligence | ✅ Análisis diferencial entre scans |

---

## Limitaciones conocidas

### Funcionales
1. **Windows binary**: Built from RC2 source (v1.4.0). To incorporate v1.5.0 source changes (settings migration, port validation), rebuild on Windows via `scripts/build_windows.ps1`.
2. **macOS**: No mantenido activamente — solo `python run.py` desde código fuente.
3. **Android APK**: Debug build (no signed para producción). Requiere que el desktop esté corriendo para funcionar. No incluye recon pipeline local.
4. **Validation engine**: Requiere tokens de sesión (cookies de autenticación del blanco) — no es completamente automático.
5. **Auto-updater**: Solo verifica y descarga actualizaciones; el usuario debe reiniciar manualmente.

### UX
1. **Sin shortcut de escritorio**: El ZIP no crea atajos ni entrada en menú de inicio.
2. **Sin webview nativo en run.sh**: Usa `--browser` por defecto si no se detecta pywebview.
3. **Sin instalador**: NSIS solo para Windows; Linux usa extracción manual del ZIP.

### Recon
1. **waybackurls**: Requiere instalación manual — `go install github.com/tomnomnom/waybackurls@latest`.
2. **subfinder/httpx/katana**: Requiere Go toolchain (`~/go/bin`) o instalación manual.
3. **Modo batch/múltiples targets**: No soportado nativamente.

---

## Requisitos de instalación

### ZIP bundle (Desktop Linux)
- **OS**: Linux x86\_64 (glibc 2.35+)
- **RAM**: 1 GB mínimo, 4 GB recomendado
- **Disco**: 500 MB libres
- **No requiere**: Python, Node.js, npm (todo incluido en el bundle)

### ZIP bundle (Desktop Windows)
- **OS**: Windows 10/11 64-bit
- **RAM**: 1 GB mínimo, 4 GB recomendado
- **Disco**: 500 MB libres
- **No requiere**: Python, Node.js, npm (todo incluido en el bundle)
- **Ejecutar**: `Windows\Rastro.exe` (doble clic o desde terminal con `--no-tray`)

### Código fuente (multiplataforma)
- **Python**: 3.10+ (3.14 recomendado)
- **Node.js**: 20+ (solo para compilar frontend)
- **RAM**: 1 GB mínimo, 4 GB recomendado

### Herramientas opcionales (mejoran cobertura)
```bash
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go install -v github.com/projectdiscovery/katana/cmd/katana@latest
go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
go install github.com/tomnomnom/waybackurls@latest
```

### AI (opcional)
- [Ollama](https://ollama.ai) con modelo `qwen2.5-coder:7b` (o compatible)

---

## Flujo recomendado de uso

### 1. Extraer e iniciar (Linux)
```bash
unzip Rastro-1.5.0-unified.zip
cd Linux
./Rastro
```

### 1. Extraer e iniciar (Windows)
```bat
Descomprimir Rastro-1.5.0-unified.zip
Abrir Windows\Rastro.exe
```

### 2. Crear un target
Abrir http://localhost:8000 (puerto configurable vía `backend_port` en settings) →
Targets → Create Target → Nombre + Dominio (ej: `acme-corp`, `*.acme.com`)

### 3. Ejecutar reconocimiento
Seleccionar target → Run Scan → esperar a que termine →
Endpoints se persisten automáticamente

### 4. Analizar superficie de ataque
Attack Surface → mapa de clusters + hot paths
Scoring → endpoints priorizados por risk\_score

### 5. Generar hipótesis
Hypotheses → Run Hypotheses → revisar cola priorizada

### 6. Investigar
Promote to Investigation → seguir pipeline:
Validation → Evidence → Findings → Report

### 7. Reportar
Reports → Generate Report → elegir formato →
HackerOne JSON / Bugcrowd HTML / Markdown

### Android
- Asegurar desktop corriendo en la misma red
- `adb install dist/rastro-android-debug.apk`
- Configurar IP del servidor en la app

---

## Notas del release

### v1.5.0 Definitive incluye
- **Root cause investigation**: 5173 port bug traced to old RC1 binary
- **Settings migration**: Auto-fix legacy `backend_port: 5173` → 8000
- **Port validation hardened**: Type + range checks with logging
- **81 tests**: Migration, port validation, browser opener, webview fallback, tray, startup/shutdown
- **Linux binary rebuilt**: PyInstaller 6.20.0, verified on port 8000
- **Definitive ZIP**: All platforms in 140 MB, audited clean
- **Full RC1 cleanup**: Old binaries, launcher, PWA shortcut removed from Windows

### v1.4.0-rc2 incluye
- **Port 5173 → 8000**: All hardcoded port references replaced
- **Lifecycle logging**: Structured boot/API/browser/shutdown logs
- **Browser/webview fallback**: Graceful degradation
- **Validation suite**: 18 automated checks via `validate_rc2.bat`
- **Bytecode verified**: RC2 binary confirmed clean

### v1.4.0-rc1 incluye
- Sprint 5: AI Provider Abstraction (registry, selector UI, SSE streaming)
- Fix `_parse_semver` para pre-release tags
- Fix `tray.py` — encoding latin-1 (em dash)
- Fix `mobile/build_apk.sh` — Java 21 compatibility
- Real-world validation documentada (9/9 stages)
- 159 tests, 0 TS errors, prebuild 16/16

### No incluye (próximas versiones)
- Recon batch/múltiples targets
- Android APK release signed
- Modo offline completo (sin dependencia Go/Ollama)
- Pipeline de validación completamente automática
- Plugin system / extensiones

---

*Para reportar bugs o sugerencias: abre un issue en el repositorio.*
