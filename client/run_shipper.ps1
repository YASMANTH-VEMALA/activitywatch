param (
    [string]$ServerUrl = "http://localhost:8000/v1/ingest",
    [string]$DeviceId = $env:COMPUTERNAME
)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " ActivityWatch Edge Shipper (Pilot Laptop Agent)" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "[*] Device ID: $DeviceId"
Write-Host "[*] Forwarding to: $ServerUrl"
Write-Host "[*] Local aw-server: http://localhost:5600"
Write-Host "[*] Press Ctrl+C to stop.`n"

python -m aw_shipper.main --device-id $DeviceId --server-url $ServerUrl

