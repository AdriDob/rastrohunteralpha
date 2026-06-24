# ANDROID_RUNTIME_CHECKLIST.md

> Matriz de validación para dispositivo Android real
> APK: `dist/release/Rastro-1.5.0-RC1.apk` (SHA256: `3228b89bc...`)
> HEAD: `ea13b53` | Fecha: 2026-06-24

---

## Preparación

```bash
# 1. Conectar dispositivo Android por USB con depuración USB activada
# 2. Verificar conexión
adb devices
#    Debe aparecer el dispositivo como "device"

# 3. Iniciar backend en la máquina de desarrollo
python3 run.py --dev

# 4. Nota: el APK usa androidScheme: "https" y cleartext: false
#    Para probar contra backend local, editar capacitor.config.json:
#      "server": {
#        "androidScheme": "http",
#        "cleartext": true,
#        "url": "http://10.0.2.2:8000"
#      }
#    Luego: npx cap copy android && cd android && ./gradlew assembleDebug

# 5. Instalar APK
adb install dist/release/Rastro-1.5.0-RC1.apk

# 6. Ver logs en tiempo real
adb logcat | grep -E "Rastro|WebView|Capacitor|rastro"
```

---

## Matriz de validación

| # | Prueba | Procedimiento | Resultado esperado | PASS/FAIL/NOT TESTED |
|---|---|---|---|---|
| 1 | **Instalación APK** | `adb install dist/release/Rastro-1.5.0-RC1.apk` | "Success" sin errores | ⬜ |
| 2 | **Apertura de app** | Tocar ícono de Rastro en launcher | App abre sin crash, sin pantalla en blanco | ⬜ |
| 3 | **Pantalla inicial (BootScreen)** | Observar pantalla de carga | Logo + spinner + progress. Sin freeze >10s | ⬜ |
| 4 | **Activación/licencia** | Navegar a /activate, ingresar license key | License key aceptada, status cambia a valid=true | ⬜ |
| 5 | **Autenticación** | Verificar que token de sesión se genere | Dashboard carga sin pedir re-login | ⬜ |
| 6 | **Dashboard** | Esperar carga completa del MissionControl | KPIs, targets, widgets renderizados. Sin errores 401/403/500 en logcat | ⬜ |
| 7 | **Persistencia (cierre/reapertura)** | Cerrar app → Reabrir | Sesión mantiene token, dashboard carga directamente (sin BootScreen si bootComplete=true) | ⬜ |
| 8 | **Orientación portrait** | Sostener dispositivo en vertical | Layout se adapta, no hay elementos cortados | ⬜ |
| 9 | **Orientación landscape** | Rotar a horizontal | Layout se reflow, no hay elementos superpuestos | ⬜ |
| 10 | **Rotación automática** | Activar auto-rotate, girar 3-4 veces | UI se reacomoda sin crash, sin blank screen, sin state loss | ⬜ |
| 11 | **Responsive teléfono** | Probar en 360x640 o similar | Menú colapsable, tarjetas se apilan verticalmente | ⬜ |
| 12 | **Responsive tablet** | Probar en 600x960 o 800x1280 | Layout de múltiples columnas, menú expandido | ⬜ |
| 13 | **Reconexión WebSocket** | Abrir app → deshabilitar WiFi → esperar 10s → reconectar WiFi | WS reconecta, eventos posteriores se reciben sin duplicados | ⬜ |
| 14 | **Manejo offline** | Deshabilitar red → navegar | Mensaje "No connection" o similar. Sin spinner infinito | ⬜ |
| 15 | **Inicio en frío** | Forzar detención (Settings > Apps > Rastro > Force Stop) → abrir | App arranca desde 0, BootScreen aparece, luego dashboard | ⬜ |
| 16 | **Reinicio** | Desde dashboard → recargar (swipe down o navegación) | Dashboard se refresca sin duplicar datos | ⬜ |

---

## Validación adicional de errores (revisar logcat)

| Error | Cómo provocarlo | Señal en logcat | PASS/FAIL |
|---|---|---|---|
| 401 sin token | Desinstalar, reinstalar, abrir sin backend | `Authorization header required` | ⬜ |
| 403 sin licencia | Desactivar license key, recargar | `License required` | ⬜ |
| WS closed | Matar backend, esperar 30s | `WebSocket closed` + reconexión | ⬜ |
| Pantalla en blanco | Rotar rápidamente 5 veces seguidas | Sin crash, sin ANR | ⬜ |
| Memory leak | Navegar entre 10+ páginas, volver al dashboard | Sin OOM, sin GC excesivo | ⬜ |

---

## Instrucciones para capturar evidencia

```bash
# Screenshot de cada paso
adb shell screencap -p /sdcard/rastro_test_01.png
adb pull /sdcard/rastro_test_01.png

# Logs de cada prueba
adb logcat -d > rastro_logcat_$(date +%Y%m%d_%H%M%S).txt

# Bugreport completo (si hay fallo)
adb bugreport rastro_bugreport_$(date +%Y%m%d_%H%M%S)
```

---

## Criterio de aprobación

| Requisito | Condición |
|---|---|
| Items 1-7 (funcionalidad core) | **TODOS PASS** |
| Items 8-12 (responsive/orientación) | **TODOS PASS** |
| Items 13-14 (red/offline) | **TODOS PASS** |
| Items 15-16 (ciclo de vida) | **TODOS PASS** |
| Errores validación adicional | **0 errores** |

**Si cualquier item core (1-7) es FAIL o NOT TESTED → DETENER RELEASE.**

---

## Checklist generado: 2026-06-24

> ⚠️ **Este checklist NO ha sido ejecutado.** La validación en dispositivo Android real debe ser realizada por el usuario en un entorno con hardware Android o emulador.
