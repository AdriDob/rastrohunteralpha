# Guía rápida: tu primer objetivo en bug bounty con Rastro

## 1. Instalación

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..
```

## 2. Iniciar Rastro

```bash
python run.py            # Modo desktop (pywebview)
python run.py --browser  # Modo navegador
```

Abrir http://localhost:8000

## 3. Crear tu primer target

1. Ir a **Targets** → **Create Target**
2. Nombre: `ejemplo-programa`
3. Dominio: `*.ejemplo.com`
4. Guardar

## 4. Ejecutar reconocimiento

1. Seleccionar el target creado
2. Pulsar **Run Scan** → modo `FAST` (minutos) o `DEEP` (más lento, mayor cobertura)
3. Esperar a que el scan termine
4. Revisar los endpoints descubiertos en la pestaña **Endpoints**

## 5. Analizar resultados

1. Ir a **Attack Surface** para ver el mapa de superficie de ataque
2. Revisar **Scoring** para ver endpoints priorizados por riesgo
3. Los endpoints con mayor `risk_score` son los más prometedores

## 6. Generar hipótesis

1. Ir a **Hypotheses** → seleccionar el target
2. Pulsar **Run Hypotheses**
3. Revisar la cola de ataque generada
4. Las hipótesis se ordenan por `priority_score` y `roi_score`

## 7. Crear investigación

1. En una hipótesis prometedora, pulsar **Promote to Investigation**
2. La investigación se crea automáticamente con timeline y progreso
3. Ir a **Investigations** para ver el detalle

## 8. Validar hallazgo

1. Dentro de la investigación, seguir el pipeline:
   - **Validation**: probar la vulnerabilidad
   - **Evidence**: revisar la evidencia recolectada
   - **Findings**: documentar el hallazgo

## 9. Generar reporte

1. Ir a **Reports** → **Generate Report**
2. Elegir formato: HackerOne JSON, Bugcrowd HTML o Markdown
3. Exportar y enviar al programa

## Atajos útiles

| Acción | Atajo |
|--------|-------|
| Command Palette | `Ctrl+K` |
| AI Copilot | `Ctrl+Shift+I` |
| Buscar targets | `Ctrl+K` → escribir nombre |

## Herramientas externas necesarias

```bash
# Instalar herramientas de descubrimiento (mejora cobertura)
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go install -v github.com/projectdiscovery/katana/cmd/katana@latest
go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
```

## Recordatorios

- Rastro es 100% local. Tus datos nunca salen de tu máquina.
- Respeta los TOS de los programas de bug bounty.
- Usa el modo DEEP solo en objetivos con scope autorizado.
- Los resultados del scoring son heurísticos; siempre validar manualmente.
