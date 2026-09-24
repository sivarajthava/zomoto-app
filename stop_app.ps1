# PowerShell Stop Script for Zomato AI Recommendation Services
Write-Host "========================================================" -ForegroundColor Yellow
Write-Host "  Stopping Zomato AI Recommendation Services" -ForegroundColor Yellow
Write-Host "========================================================" -ForegroundColor Yellow

# 1. Stop background PowerShell jobs if any exist
Get-Job -Name "FastAPI", "Streamlit" -ErrorAction SilentlyContinue | Stop-Job -ErrorAction SilentlyContinue | Remove-Job -ErrorAction SilentlyContinue

# 2. Stop processes listening on port 8000 (FastAPI)
$conn8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($conn8000) {
    $pids8000 = $conn8000 | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($targetPid in $pids8000) {
        if ($targetPid -and $targetPid -ne 0) {
            Write-Host "Stopping FastAPI backend (PID: $targetPid on port 8000)..." -ForegroundColor Cyan
            Stop-Process -Id $targetPid -Force -ErrorAction SilentlyContinue
        }
    }
} else {
    Write-Host "Port 8000 (FastAPI) is not active." -ForegroundColor Gray
}

# 3. Stop processes listening on port 8501 (Streamlit)
$conn8501 = Get-NetTCPConnection -LocalPort 8501 -ErrorAction SilentlyContinue
if ($conn8501) {
    $pids8501 = $conn8501 | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($targetPid in $pids8501) {
        if ($targetPid -and $targetPid -ne 0) {
            Write-Host "Stopping Streamlit frontend (PID: $targetPid on port 8501)..." -ForegroundColor Cyan
            Stop-Process -Id $targetPid -Force -ErrorAction SilentlyContinue
        }
    }
} else {
    Write-Host "Port 8501 (Streamlit) is not active." -ForegroundColor Gray
}

Write-Host "`nAll Zomato AI services stopped successfully." -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Yellow
