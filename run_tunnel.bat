@echo off
title ActivityWatch Public HTTPS Tunnel (ngrok)
echo ==========================================================
echo Starting Public HTTPS Tunnel for Remote Laptops
echo ==========================================================
echo [*] Exposing port 8000 to public internet...
echo.

ngrok http 8000
pause

