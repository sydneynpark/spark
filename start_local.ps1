$root = $PSScriptRoot

Write-Host "Starting backend API on http://localhost:5000 ..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\backend'; python run_local.py"

Write-Host "Starting frontend on http://localhost:3000 ..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npm start"

Write-Host ""
Write-Host "Both servers are starting in separate windows."
Write-Host "  Frontend: http://localhost:3000"
Write-Host "  Backend:  http://localhost:5000"
