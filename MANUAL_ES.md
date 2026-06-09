# Rastro — Manual de uso (Español)

## Introducción

Rastro es una herramienta local-first de apoyo a recon y priorización para bug bounty. Se enfoca en detectar endpoints de alto valor (APIs, GraphQL, paneles admin, multi-tenant) y priorizarlos con heurísticas deterministas.

Este manual es para usuarios principiantes que quieren ejecutar Rastro localmente y entender el flujo.

---

## Qué hace (y qué no hace)

- Hace: ejecuta herramientas locales de recon (subfinder, wayback, katana, httpx), normaliza endpoints, los puntúa con reglas heurísticas y muestra un digest de alto valor.
- No hace: scrapping agresivo de plataformas, entrenamiento ML, explotación automática de vulnerabilidades.

---

## Requisitos previos (resumen)

- Python 3.12+ (el entorno de desarrollo usa 3.14 en el repo)
- Virtualenv
- Herramientas opcionales que aumentan la cobertura:
  - `subfinder`
  - `katana`
  - `httpx` (CLI runner incluido)
  - `nuclei` (opcional)
  - `gowitness` (opcional, para capturas)
- (Opcional) `Ollama` para resúmenes AI locales

---

## Instalación rápida

```bash
cd /home/tuusuario/Rastro
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8000
# en otra terminal
streamlit run dashboard/app.py
```

---

## Flujo básico (paso a paso)

1. Abrir el dashboard (Streamlit) y en la pestaña `Targets` crear un target (nombre y dominio).
2. Seleccionar el target y pulsar `Run Scan` en la pestaña `Recon` (elige modo: FAST/DEEP/API).
3. Esperar a que el scan termine; el sistema persistirá endpoints normalizados en la base de datos.
4. Revisar la pestaña `High Signal` y `Targets Intelligence` para ver prioridades y acciones.
5. Si deseas analizar un endpoint en detalle, usa `Endpoints` → selecciona endpoint → `Generar AI summary` (si está disponible Ollama).

---

## Interpretación del Digest

- Cada entrada trae una `risk_score` calculada por heurísticas deterministas.
- Prioriza APIs, GraphQL, admin, multi-tenant y endpoints con indicios de `auth`.
- `noise` indica probabilidad de activos estáticos o marketing.

---

## Troubleshooting rápido

- Si `Run Scan` falla:
  - Revisa que las herramientas externas estén instaladas.
  - Revisa `targets/<nombre>/logs` para ver los logs generados.
  - Aumenta `SCAN_TIMEOUT` en variables de entorno si tu red es lenta.
- Si el dashboard no muestra endpoints:
  - Confirma que `normalized_endpoints.json` existe en `targets/<nombre>/endpoints/`.
  - Comprueba que `endpoints` están insertados en la base de datos (chequear `database/rastro.db`).

---

## Primeros pasos — herramientas (instalación rápida)

- subfinder: https://github.com/projectdiscovery/subfinder
- katana: https://github.com/projectdiscovery/katana
- httpx: https://github.com/projectdiscovery/httpx
- nuclei: https://github.com/projectdiscovery/nuclei
- gowitness: https://github.com/sensepost/gowitness
- Ollama: https://ollama.com/ (opcional)

(En la sección `First-run setup` del README se incluyen comandos sugeridos.)

---

## Buenas prácticas

- Ejecuta scans en ambientes controlados y respeta TOS.
- Mantén actualizado el entorno virtual y las herramientas externas.
- Revisa y ajusta pesos de scoring según tus observaciones.

---

Si quieres, puedo traducir/ajustar este manual para equipos o añadir ejemplos concretos.
