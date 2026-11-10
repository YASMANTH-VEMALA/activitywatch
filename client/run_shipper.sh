#!/usr/bin/env bash
# ============================================================================
# ActivityWatch Edge Shipper Launcher for macOS / Linux Pilot Laptops
# ============================================================================

SERVER_URL=${1:-"http://localhost:8000/v1/ingest"}
DEVICE_ID=${2:-$(hostname -s)}

echo "=========================================================="
echo " ActivityWatch Edge Shipper (macOS / Linux)"
echo "=========================================================="
echo "[*] Device ID: $DEVICE_ID"
echo "[*] Forwarding to: $SERVER_URL"
echo "[*] Local aw-server: http://localhost:5600"
echo "[*] Press Ctrl+C to stop."
echo ""

python3 -m aw_shipper.main --device-id "$DEVICE_ID" --server-url "$SERVER_URL"

