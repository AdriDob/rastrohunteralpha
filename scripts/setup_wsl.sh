#!/usr/bin/env bash
set -euo pipefail

echo "Instalando dependencias básicas (WSL Ubuntu)"
sudo apt update && sudo apt install -y build-essential git curl wget jq

echo "Instalar Go (si no está) para herramientas basadas en Go..."
# Aquí el operador puede instalar subfinder, gau, waybackurls, nuclei, ffuf, etc.

echo "Comandos recomendados (ejecutar manualmente):"
cat <<'EOF'
# ejemplo: instalar subfinder
# GO111MODULE=on go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
# instalar httpx
# GO111MODULE=on go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
# instalar gau
# GO111MODULE=on go install -v github.com/lc/gau/v2/cmd/gau@latest
# instalar waybackurls
# GO111MODULE=on go install -v github.com/tomnomnom/waybackurls@latest
# instalar nuclei
# GO111MODULE=on go install -v github.com/projectdiscovery/nuclei/v2/cmd/nuclei@latest
EOF

echo "Setup inicial completado. Instale las herramientas Go usando los comandos anteriores."
