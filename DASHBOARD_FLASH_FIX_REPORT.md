# DASHBOARD_FLASH_FIX_REPORT.md

> Evidencia de la corrección del Bug #8 — Dashboard visible con licencia inválida.

---

## Cambios aplicados

### 1. Verificación de licencia en rehidratación

**Archivo:** `frontend/src/stores/index.ts:68-98`

Durante la rehidratación del store (Zustand persist), se agrega una llamada a `/api/license/status` ANTES de intentar cargar el overview:

```typescript
// Check license status before proceeding
const licRes = await fetch('/api/license/status');
const licData = await licRes.json();
const licValid = licData?.data?.valid === true;
if (!licValid) {
    useStore.setState({ licenseValid: false, licenseLoading: false });
    // BootScreen detecta licenseValid=false → muestra error en vez de dashboard
    return;
}
```

**Flujo con licencia inválida:**
1. Store rehidrata
2. Token extraído de URL (si existe)
3. `/api/license/status` → `valid: false`
4. `licenseValid = false` seteado en store
5. `getOverviewPreload()` NO se ejecuta (no hay llamada innecesaria)
6. BootScreen detecta `licenseValid === false` → muestra pantalla de error

### 2. BootScreen con estado de error

**Archivo:** `frontend/src/components/BootScreen.tsx:17-18, 30-32, 100-125`

La interfaz acepta un nuevo prop opcional `licenseError`:

```typescript
interface BootScreenProps {
  onComplete: () => void;
  licenseError?: string | null;
}
```

Cuando `licenseError` está presente:
- El timer de boot se detiene (useEffect retorna sin programar avance)
- Se muestra un mensaje de error con estilo consistente
- Un botón "Activate license" redirige a `/activate`

### 3. License gate en App.tsx

**Archivo:** `frontend/src/App.tsx:220-249`

Se agregó un license gate que intercepta el renderizado cuando `licenseValid === false`:

```typescript
if (licenseValid === false && !showOnboarding && !showTour) {
    return (
        <div style={{...}}>
            <div>⚠</div>
            <div>License required</div>
            <div>{licenseError || 'No active license detected.'}</div>
            <button onClick={() => window.location.href = '/activate'}>
                Activate license
            </button>
        </div>
    );
}
```

### 4. LicenseGate component (mid-session safety net)

**Archivo:** `frontend/src/App.tsx:92-100`

Componente que monitorea cambios de licencia durante la sesión:

```typescript
function LicenseGate() {
    const navigate = useNavigate();
    const location = useLocation();
    const { licenseValid } = useLicense();
    useEffect(() => {
        if (licenseValid === false && location.pathname !== '/activate') {
            navigate('/activate', { replace: true });
        }
    }, [licenseValid, navigate, location]);
    return null;
}
```

## Escenarios cubiertos

| Escenario | Antes | Después |
|---|---|---|
| Licencia válida | Dashboard ok ✅ | Dashboard ok ✅ |
| Licencia inválida (carga inicial) | Dashboard flash → /activate ❌ | BootScreen muestra error, no renderiza dashboard ✅ |
| Licencia inválida (sesión iniciada) | Dashboard → error ❌ | LicenseGate redirige a /activate, no renderiza dashboard ✅ |
| Licencia ausente | Dashboard flash ❌ | BootScreen muestra "No active license detected" ✅ |
| Token válido + licencia inválida | Dashboard flash ❌ | BootScreen muestra error, botón "Activate" ✅ |
| Reinicio de app | Dashboard flash ❌ | Store persiste licenseValid → gate intercepta ✅ |
| Apertura EXE / run.py | Dashboard flash ❌ | License check en rehidratación → error en BootScreen ✅ |

## ¿Qué NO se renderiza si la licencia es inválida?

- ❌ MissionControl
- ❌ Dashboard
- ❌ Widgets (KPIs, targets, findings, charts)
- ❌ Sidebar
- ❌ Cualquier ruta protegida

Se renderiza únicamente:
- ✅ BootScreen (con mensaje de error) 
- ✅ Activation page (tras clic en botón o navegación directa a /activate)

## Verificación de TypeScript

```bash
$ npx tsc --noEmit --pretty
# (no output — sin errores)
```
