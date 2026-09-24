@echo off
echo ========================================================
echo   Starting Zomato AI Recommendation Services
echo ========================================================
echo.
echo 1. Launching FastAPI Backend on http://127.0.0.1:8000 ...
start "Zomato - FastAPI Backend" cmd /k ".\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000 --reload"

echo 2. Launching Streamlit Frontend on http://localhost:8501 ...
start "Zomato - Streamlit Frontend" cmd /k ".\.venv\Scripts\streamlit.exe run app/ui/streamlit_app.py --server.port 8501"

echo.
echo Both services are running in separate terminal windows.
echo - DineMind AI Web UI: http://127.0.0.1:8000/ (or http://127.0.0.1:8000/app)
echo - FastAPI Docs:       http://127.0.0.1:8000/docs
echo - Streamlit UI:       http://localhost:8501
echo ========================================================
