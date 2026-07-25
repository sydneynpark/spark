$root = $PSScriptRoot

$lanIp = (Get-NetIPConfiguration |
    Where-Object { $_.IPv4DefaultGateway -and $_.NetAdapter.Status -eq 'Up' } |
    Select-Object -First 1 -ExpandProperty IPv4Address |
    Select-Object -First 1 -ExpandProperty IPAddress)

if (-not $lanIp) {
    Write-Host "Could not detect a LAN IP, falling back to localhost (phone access won't work)."
    $lanIp = 'localhost'
}

Write-Host "Starting backend API on http://${lanIp}:5000 ..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\backend'; python run_local.py"

Write-Host "Starting frontend on http://${lanIp}:3000 ..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; `$env:REACT_APP_API_URL='http://${lanIp}:5000'; `$env:REACT_APP_CDN_URL='http://${lanIp}:5000/cdn'; `$env:REACT_APP_COVERS_CDN_URL='http://${lanIp}:5000/cdn/books'; npm start"

Write-Host ""
Write-Host "Both servers are starting in separate windows."
Write-Host "  Frontend: http://${lanIp}:3000  (also reachable at http://localhost:3000 on this PC)"
Write-Host "  Backend:  http://${lanIp}:5000"
