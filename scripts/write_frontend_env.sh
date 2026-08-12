#!/bin/bash
# Writes .vscode/.env.local with the frontend's API URLs, pointed at this
# Mac's LAN IP so phone testing keeps working when launched from VS Code
# (mirrors the LAN detection in start_local.sh).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

iface=$(route -n get default 2>/dev/null | awk '/interface: /{print $2}')
lan_ip=$(ipconfig getifaddr "$iface" 2>/dev/null || true)

if [ -z "$lan_ip" ]; then
    lan_ip="localhost"
fi

mkdir -p "$ROOT/.vscode"
cat > "$ROOT/.vscode/.env.local" <<EOF
REACT_APP_API_URL=http://$lan_ip:5000
REACT_APP_CDN_URL=http://$lan_ip:5000/cdn
REACT_APP_COVERS_CDN_URL=http://$lan_ip:5000/cdn/books
EOF
