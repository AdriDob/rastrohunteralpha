# Instalación de Rastro

---

## Android (APK)

### Requisitos
- Linux o macOS
- Node.js 18+
- Java 17, 18, 19, 20 o 21 (JDK) — NO usar Java 22+
- Android SDK (o usar `--install-sdk`)

### Compilar APK

```bash
# 1. Clonar
git clone https://github.com/tu-usuario/rastro.git
cd rastro

# 2. Compilar frontend + APK
./mobile/build_apk.sh

# Si no tenés Android SDK instalado:
./mobile/build_apk.sh --install-sdk

# APK generado en:
#   android/app/build/outputs/apk/debug/app-debug.apk
```

### Instalar en dispositivo
```bash
adb install android/app/build/outputs/apk/debug/app-debug.apk
```

### Notas
- El APK se conecta al backend del desktop via API REST.
- Necesitás el desktop corriendo para funcionalidad completa.
- La app móvil tiene su propio login (no comparte sesión con desktop).
- Para release firmado: `./mobile/build_apk.sh --release` (requiere keystore).

---

## Windows (ejecutable portátil)

### Requisitos
- Windows 10 u 11 (64-bit)
- Python 3.10+ (para compilar, no para ejecutar)
- Node.js 20+ (para compilar el frontend)
- Microsoft Edge WebView2 (viene incluido en Windows 11)

### Compilar

```powershell
# 1. Clonar
git clone https://github.com/tu-usuario/rastro.git
cd rastro

# 2. Instalar dependencias Python
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 3. Compilar
scripts\build_windows.ps1
```

El ejecutable se genera en `dist\Rastro\Rastro.exe`.

### Ejecutar

```
dist\Rastro\Rastro.exe
```

O desde código:

```
python run.py
```

### Instalación completa (opcional)

Como administrador:

```powershell
powershell -ExecutionPolicy Bypass desktop\build\install_windows.ps1
```

Esto copia Rastro a `%ProgramFiles%\Rastro\` y crea accesos directos en Inicio.

---

## Linux

### Requisitos
- Python 3.10+
- Node.js 20+
- Go 1.22+ (para herramientas de descubrimiento)

### Compilar

```bash
# 1. Clonar
git clone https://github.com/tu-usuario/rastro.git
cd rastro

# 2. Instalar dependencias
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd frontend && npm install && npm run build && cd ..

# 3. Compilar binario (opcional)
./scripts/build_linux.sh
```

### Ejecutar

```bash
# Modo desktop (pywebview, requiere display)
python run.py

# Modo navegador
python run.py --browser

# Modo dev (hot-reload frontend)
python desktop/main_desktop.py --dev --browser
```

---

## macOS

> Soporte comunitario (no mantenido activamente).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..
python run.py
```

---

## Desarrollo

```bash
# Terminal 1: Backend
uvicorn api.main:app --reload --port 8000

# Terminal 2: Frontend (hot-reload)
cd frontend && npm run dev

# Abrir http://localhost:5173
```

---

## Verificación

```bash
# Backend responde
curl http://127.0.0.1:8000/api/health

# Tests
python -m pytest tests/ -v
```

---

## Dependencias del sistema

### Windows
- Microsoft Edge WebView2 (incluido en Win11, descargable para Win10)
- Go tools: `go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest` (y katana, httpx)

### Linux
```bash
sudo apt install python3 python3-venv nodejs npm golang
pip install -r requirements.txt
```

---

## Solución de problemas

### `webview` no arranca / error de GTK
```bash
# Linux: instalar dependencias de pywebview
sudo apt install libgtk-3-dev libwebkit2gtk-4.1-dev

# Fallback: usar modo navegador
python run.py --browser
```

### Puerto 8000 ocupado
Rastro elige automáticamente el puerto configurado. Si querés usar otro:
```bash
# En settings.json (AppData/Rastro o ~/.rastro):
# {"backend_port": 8001}
```

### Frontend build falla
```bash
cd frontend
rm -rf node_modules dist
npm install
npm run build
```

### Go tools (subfinder/katana/httpx) no encontradas
```bash
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go install -v github.com/projectdiscovery/katana/cmd/katana@latest
go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
# Asegurate que ~/go/bin esté en PATH
```

### WebView2 no disponible (Windows 10)
- Descargar e instalar desde: https://developer.microsoft.com/en-us/microsoft-edge/webview2/
- O usar `python run.py --browser` como fallback

### Database corruption
```bash
# Rastro usa SQLite en database/rastro.db.
# Si se corrompe, eliminarlo y reiniciar (se recrea automáticamente):
rm database/rastro.db   # Linux
del %LOCALAPPDATA%\Rastro\database\rastro.db   # Windows
```
