# Rastro Frontend

React 19 + TypeScript + Vite 8 dashboard for attack surface management.

## Quick start

```bash
npm install
npm run dev        # dev server → http://localhost:5173
npm run build      # production → frontend/dist/
npm run preview    # preview production build
```

## Pages

22 routes with lazy loading:
- `Overview`, `Targets`, `Endpoints`, `Findings`, `Vulnerabilities`
- `Attack Surface`, `Quick Wins`, `Opportunities`, `ROI`
- `Scans`, `Digest`, `Verdicts`, `Reports`, `Hypotheses`
- `Pipeline`, `Attack`, `Validation`, `Operations`
- `Assistant`, `Differential Intelligence`, `Contracts`, `Settings`

## Conventions

- **State**: React context (no Redux/RTK).
- **Routing**: react-router with `Suspense` + lazy imports.
- **Styling**: Tailwind CSS v4.
- **Copilot**: AI sidebar powered by Ollama/OpenAI.
- **Layout**: `Sidebar` + `TopBar` + `CommandPalette`.

## Proxy

In dev mode, `/api/*` proxies to `http://127.0.0.1:8000`.
In production, the desktop wrapper serves both the API and static frontend on the same origin.
