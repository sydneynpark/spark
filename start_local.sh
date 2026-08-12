#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

iface=$(route -n get default 2>/dev/null | awk '/interface: /{print $2}')
lan_ip=$(ipconfig getifaddr "$iface" 2>/dev/null || true)

if [ -z "$lan_ip" ]; then
    echo "Could not detect a LAN IP, falling back to localhost (phone access won't work)."
    lan_ip="localhost"
fi

backend_cmd="cd '$ROOT/backend' && .venv/bin/python run_local.py"
frontend_cmd="cd '$ROOT/frontend' && REACT_APP_API_URL='http://$lan_ip:5000' REACT_APP_CDN_URL='http://$lan_ip:5000/cdn' REACT_APP_COVERS_CDN_URL='http://$lan_ip:5000/cdn/books' npm start"

echo "Starting backend API on http://$lan_ip:5000 ..."
osascript -e "tell application \"Terminal\" to do script \"$backend_cmd\""

echo "Starting frontend on http://$lan_ip:3000 ..."
osascript -e "tell application \"Terminal\" to do script \"$frontend_cmd\""

echo ""
echo "Both servers are starting in separate Terminal windows."
echo "  Frontend: http://$lan_ip:3000  (also reachable at http://localhost:3000 on this Mac)"
echo "  Backend:  http://$lan_ip:5000"
