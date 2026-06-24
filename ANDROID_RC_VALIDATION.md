# ANDROID_RC_VALIDATION.md

> Validación del artefacto Android RC1
> HEAD: `e0f179b` | Fecha: 2026-06-24

---

## Artefacto generado

| Ítem | Valor |
|---|---|
| APK | `dist/release/Rastro-1.5.0-RC1.apk` (debug-signed, instalable) |
| SHA256 | `3228b89bc62316bd4518eee40d656ca3ab9447b95a182e2c75f9e475074c4629` |
| Tamaño | 4.4 MB |
| Build | `./gradlew assembleDebug` |
| JDK | Temurin-21.0.6+7 (OpenJDK 21.0.6) |
| Android SDK | compileSdk 36, minSdk 24, targetSdk 36 |
| Capacitor | v8.4.0 |
| Frontend | Build `npm run build` (TypeScript + Vite) |
| Firma | Debug key (Android debug) |

## Estructura interna

| Componente | Archivos | Tamaño |
|---|---|
| DEX (código compilado) | 6 clases (`classes.dex` – `classes6.dex`) | ~8.7 MB |
| Frontend web | `assets/public/index.html`, `manifest.json`, `service-worker.js`, chunks JS/CSS | 1.4 KB + chunks |
| Recursos Android | `AndroidManifest.xml`, resources | Incluido |
| Librerías nativas | Ninguna | N/A |

### Verificación de assets frontend

Todos los archivos del build de Vite están incluidos en `assets/public/` dentro del APK:
- `index.html` (1410 bytes)
- `manifest.json` (735 bytes)
- `favicon.svg` (9522 bytes)
- `service-worker.js` (4584 bytes)
- Múltiples chunks JS de código lazy-loaded

---

## Validación estática (realizada en este entorno)

### Build system

| Verificación | Resultado |
|---|---|
| Compilación DEX | ✅ 6 classes.dex generados sin errores |
| Sincronización Capacitor | ✅ `npx cap copy android` exitoso |
| Frontend build previo | ✅ `npm run build` exitoso (0 errores TS) |
| Versión Java | ✅ OpenJDK 21.0.6 LTS (Temurin) |
| Android SDK | ✅ compileSdk 36, minSdk 24 |
| APK firmado | ✅ Debug key |

### Backend API (compartido con el mismo frontend)

> Las mismas rutas de API que usa la app Android ya fueron validadas en RC_VALIDATION_REPORT.md

| Endpoint | Estado | Detalle |
|---|---|---|
| `GET /api/health` | ✅ | `{"status":"ok","version":"1.5.0"}` |
| `GET /api/license/status` | ✅ | `{"data":{"valid":true}}` |
| `GET /api/auth/*` | ✅ | Autenticación funcional |
| `GET /api/system/state` | ✅ | JSON correcto |
| `GET /api/operations/notifications` | ✅ | `{"items":[]}` sin errores |

### Capacitor configuration

```json
{
  "appId": "ai.rastro.app",
  "appName": "Rastro",
  "webDir": "frontend/dist",
  "server": {
    "androidScheme": "https",
    "cleartext": false
  }
}
```

El APK fue configurado con `androidScheme: "https"` y `cleartext: false` — conexiones solo por HTTPS.

---

## Validación en dispositivo real (NO REALIZADA)

> ⚠️ **Este entorno (WSL2 terminal sin display, sin emulador, sin dispositivo Android conectado) no permite ejecutar la app Android.** Las siguientes pruebas requieren un dispositivo físico o emulador.

| Prueba | Estado | Requiere |
|---|---|---|
| 1. Instalación real | ⏳ Pendiente | Dispositivo Android o emulador |
| 2. Apertura | ⏳ Pendiente | Dispositivo Android o emulador |
| 3. Onboarding | ⏳ Pendiente | Dispositivo Android o emulador |
| 4. Activación | ⏳ Pendiente | Dispositivo Android o emulador |
| 5. Autenticación | ⏳ Pendiente | Dispositivo Android o emulador |
| 6. Dashboard | ⏳ Pendiente | Dispositivo Android o emulador |
| 7. Persistencia | ⏳ Pendiente | Dispositivo Android o emulador |
| 8. Portrait | ⏳ Pendiente | Dispositivo Android o emulador |
| 9. Landscape | ⏳ Pendiente | Dispositivo Android o emulador |
| 10. Rotación automática | ⏳ Pendiente | Dispositivo Android o emulador |
| 11. Responsive teléfono | ⏳ Pendiente | Dispositivo Android o emulador |
| 12. Responsive tablet | ⏳ Pendiente | Dispositivo Android o emulador |

### Instrucciones para validación local

```bash
# 1. Instalar el APK en dispositivo/emulador
adb install dist/release/Rastro-1.5.0-RC1.apk

# 2. La app se conecta al servidor backend configurado en capacitor.config.json
# Por defecto usa HTTPS (androidScheme: "https", cleartext: false)
# Para desarrollo local, cambiar a:
#   "server": {
#     "androidScheme": "http",
#     "cleartext": true,
#     "url": "http://10.0.2.2:8000"
#   }

# 3. Verificar que el backend esté corriendo en el host:
#    python3 run.py --dev
```

---

## Conclusión

| Componente | Estado |
|---|---|
| Build APK (Java 21, Gradle) | ✅ Exitoso |
| Frontend sync (Capacitor) | ✅ Exitoso |
| Estructura APK | ✅ Válida (6 classes.dex, assets incluidos) |
| Firma | ✅ Debug key |
| Pruebas en dispositivo | ⏳ **Pendientes — requieren entorno Android** |
| **¿APK válida para release?** | **⚠️ Estructuralmente correcta, falta validación en dispositivo** |

Para completar la validación, ejecutar en un entorno con Android SDK/emulador:
1. `adb install dist/release/Rastro-1.5.0-RC1.apk`
2. Abrir la app
3. Verificar onboarding, activación, auth, dashboard, persistencia
4. Probar rotación, portrait/landscape, responsive
5. Documentar resultados en este mismo archivo
