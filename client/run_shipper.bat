@echo off
REM ============================================================================
REM ActivityWatch Edge Shipper Launcher for Windows Pilot Laptops
REM ============================================================================

set INGEST_SERVER_URL=%1
set AW_DEVICE_ID=%2

if "%INGEST_SERVER_URL%"=="" (
    set INGEST_SERVER_URL=https://unaroused-frontlessly-ramona.ngrok-free.dev/v1/ingest
)

if "%AW_DEVICE_ID%"=="" (
    set AW_DEVICE_ID=%COMPUTERNAME%
)

echo ==========================================================================
echo [*] ActivityWatch Enterprise Edge Shipper
echo [*] Device ID: %AW_DEVICE_ID%
echo [*] Forwarding to: %INGEST_SERVER_URL%
echo [*] Target local aw-server: http://localhost:5600
echo ==========================================================================

REM Full day reset sync pass ensures 1:1 parity with ActivityWatch localhost:5600
python -m aw_shipper.main --reset --device-id %AW_DEVICE_ID% --server-url %INGEST_SERVER_URL%
pause

