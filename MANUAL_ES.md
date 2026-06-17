# Rastro — Manual de uso (Español)

## Introducción

Rastro es un sistema operativo privado de investigación para analistas de bug bounty y attack surface intelligence. Corre 100% local, sin dependencia cloud.

Este manual es para usuarios que quieren ejecutar Rastro y entender el flujo completo.

---

## Qué hace (y qué no hace)

- Hace: ejecuta herramientas locales de recon (subfinder, wayback, katana, httpx), normaliza endpoints, los puntúa con reglas heurísticas, genera hipótesis, valida hallazgos, produce reportes en formatos HackerOne/Bugcrowd.
- No hace: scrapping agresivo de plataformas, entrenamiento ML, explotación automática de vulnerabilidades.

---

## Requisitos previos

- Python 3.10+
- Node.js 20+ (para compilar frontend)
- Herramientas de descubrimiento (opcional pero recomendado):
  - `subfinder`, `katana`, `httpx` (Go binaries en `~/go/bin`)
  - `nuclei`, `gowitness` (opcionales)
- (Opcional) `Ollama` para resúmenes AI locales

---

## Instalación rápida

```bash
git clone <repo-url> rastro
cd rastro

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd frontend && npm install && npm run build && cd ..

python run.py
```

Esto inicia Rastro en modo desktop (pywebview). También se puede usar en navegador:

```bash
python run.py --browser
```

---

## Flujo básico (paso a paso)

1. Abrir Rastro en el navegador o desktop app.
2. Ir a **Targets** → crear un target (nombre y dominio).
3. Ir al target y pulsar **Run Scan** (modo FAST/DEEP/API).
4. Esperar a que el scan termine; los endpoints se persisten automáticamente.
5. Revisar **Scoring** y **Attack Surface** para ver prioridades.
6. Generar **Hypotheses** desde el panel de hipótesis.
7. Promover una hipótesis a **Investigation**.
8. En la investigación, seguir el pipeline: Validation → Evidence → Findings → Report.
9. Exportar el reporte a HackerOne JSON, Bugcrowd HTML o Markdown.

---

## Interpretación del Scoring

- Cada endpoint recibe un `risk_score` calculado por heurísticas deterministas.
- Prioriza APIs, GraphQL, admin, multi-tenant y endpoints con indicios de `auth`.
- `noise` indica probabilidad de activos estáticos o marketing.

---

## Atajos de teclado

- `Ctrl+K` — Command Palette (búsqueda global, navegación rápida)
- `Ctrl+Shift+I` — AI Copilot contextual

---

## Primeros pasos — herramientas (instalación rápida)

```bash
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go install -v github.com/projectdiscovery/katana/cmd/katana@latest
go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
go install -v github.com/sensepost/gowitness@latest
```

Asegurate que `~/go/bin` esté en tu PATH.

---

## Buenas prácticas

- Ejecuta scans en ambientes controlados y respeta TOS de los programas.
- Mantén actualizado el entorno virtual y las herramientas externas.
- Revisa y ajusta pesos de scoring según tus observaciones.
- Usa el modo DEEP solo en objetivos con scope autorizado.
