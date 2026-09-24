# PowerShell Launcher Script for Zomato AI Recommendation Services
Write-Host "========================================================" -ForegroundColor Green
Write-Host "  Starting Zomato AI Recommendation Services" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green

Write-Host "`n1. Launching FastAPI Backend on http://127.0.0.1:8000 ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", ".\.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

Write-Host "2. Launching Streamlit Frontend on http://localhost:8501 ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", ".\.venv\Scripts\streamlit run app/ui/streamlit_app.py --server.port 8501"

Write-Host "`nBoth services launched in separate windows!" -ForegroundColor Green
Write-Host "- DineMind AI Web UI   : http://127.0.0.1:8000/ (or http://127.0.0.1:8000/app)" -ForegroundColor Yellow
Write-Host "- FastAPI Swagger Docs : http://127.0.0.1:8000/docs" -ForegroundColor Yellow
Write-Host "- Streamlit Frontend   : http://localhost:8501" -ForegroundColor Yellow
Write-Host "========================================================" -ForegroundColor Green
