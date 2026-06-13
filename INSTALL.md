# Instalación de Rastro

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
