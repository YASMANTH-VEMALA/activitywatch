@echo off
title ActivityWatch Enterprise Backend Server
echo ==========================================================
echo Starting ActivityWatch Central Ingest & Dashboard Server
echo ==========================================================
echo [*] Web Dashboard: http://localhost:8000
echo [*] API Documentation: http://localhost:8000/docs
echo.

if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

python -m uvicorn server.main:app --host 0.0.0.0 --port 8000
pause

