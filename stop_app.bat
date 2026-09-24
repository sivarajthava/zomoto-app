@echo off
echo ========================================================
echo   Stopping Zomato AI Recommendation Services
echo ========================================================
echo.

echo Stopping FastAPI on port 8000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    echo Terminating PID: %%a
    taskkill /F /PID %%a >nul 2>&1
)

echo Stopping Streamlit on port 8501...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8501 ^| findstr LISTENING') do (
    echo Terminating PID: %%a
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo All Zomato AI services stopped.
echo ========================================================
