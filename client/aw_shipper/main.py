import time
import sys
import os
import argparse
from datetime import datetime, date, time as dtime, timezone, timedelta
from .config import ShipperConfig
from .outbox import SQLiteOutbox
from .redaction import RedactionEngine
from .aw_client import AWLocalClient
from .shipper import HTTPShipper

def run_sync_cycle(config: ShipperConfig, outbox: SQLiteOutbox, aw_client: AWLocalClient, redaction: RedactionEngine, shipper: HTTPShipper, full_day: bool = False):
    # 1. Discover local buckets
    buckets = aw_client.get_buckets()
    if not buckets:
        print("[!] No ActivityWatch buckets found. Please verify aw-server is running on http://localhost:5600")
        return

    target_bucket_prefixes = ["aw-watcher-window", "aw-watcher-afk", "aw-watcher-web", "aw-watcher-vscode"]

    total_enqueued = 0
    for b_id, b_meta in buckets.items():
        if not any(b_id.startswith(prefix) for prefix in target_bucket_prefixes):
            continue

        cursor = None if full_day else outbox.get_cursor(b_id, overlap_minutes=config.overlap_window_minutes)
        if not cursor:
            # Query from 24 hours ago to capture the full day's telemetry regardless of timezone
            cursor = datetime.now(timezone.utc) - timedelta(hours=24)

        print(f"[*] Querying events for bucket '{b_id}' (since {cursor.strftime('%H:%M:%S UTC')})...")
        events = aw_client.get_events(b_id, start_time=cursor, limit=-1)

        if events:
            # Apply local redaction
            cleaned_events = [redaction.scrub_event(e) for e in events]
            
            # Enqueue in chunks of 500 to keep network transmissions responsive
            chunk_size = 500
            for i in range(0, len(cleaned_events), chunk_size):
                outbox.enqueue_batch(config.device_id, b_id, cleaned_events[i:i + chunk_size])
            total_enqueued += len(cleaned_events)

            # Update bucket cursor to latest timestamp
            latest_time = max(datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00")) for e in events)
            outbox.update_cursor(b_id, latest_time)
            print(f"  [+] Enqueued {len(cleaned_events)} events for '{b_id}' (latest: {latest_time.strftime('%H:%M:%S')})")

    # 2. Flush pending outbox batches over HTTPS
    sent = shipper.flush_outbox()

    # 3. Send heartbeat
    shipper.send_heartbeat()
    return total_enqueued

def main():
    parser = argparse.ArgumentParser(description="ActivityWatch Enterprise Edge Shipper Daemon")
    parser.add_argument("--once", action="store_true", help="Run a single sync pass and exit")
    parser.add_argument("--reset", action="store_true", help="Reset local outbox and cursor checkpoints to force a 100% full-day re-sync")
    parser.add_argument("--device-id", type=str, help="Override device ID (e.g. dev-pilot-laptop-01 or hostname)")
    parser.add_argument("--server-url", type=str, help="Central Ingest API URL (e.g. https://...ngrok-free.dev/v1/ingest)")
    args = parser.parse_args()

    config = ShipperConfig()
    if args.device_id:
        config.device_id = args.device_id
    if args.server_url:
        config.server_url = args.server_url

    outbox = SQLiteOutbox(config.sqlite_db_path)
    if args.reset:
        print("[*] Resetting local outbox database and bucket cursors...")
        outbox.reset()
        print("[✓] Local cursors reset. Shipper will capture the entire day from midnight.")

    redaction = RedactionEngine(config.redaction_patterns)
    aw_client = AWLocalClient(config.aw_server_url)
    shipper = HTTPShipper(config, outbox)

    print(f"[*] ActivityWatch Shipper started. Device ID: {config.device_id}")
    print(f"[*] Forwarding to: {config.server_url} (Sync interval: {config.sync_interval_seconds}s)")

    if args.once:
        run_sync_cycle(config, outbox, aw_client, redaction, shipper, full_day=args.reset)
        print("[+] Single sync cycle completed successfully.")
        return

    try:
        # First cycle runs full day if reset was requested
        first_pass = True
        while True:
            run_sync_cycle(config, outbox, aw_client, redaction, shipper, full_day=(args.reset and first_pass))
            first_pass = False
            time.sleep(config.sync_interval_seconds)
    except KeyboardInterrupt:
        print("\n[!] Shipper stopped by user.")

if __name__ == "__main__":
    main()

