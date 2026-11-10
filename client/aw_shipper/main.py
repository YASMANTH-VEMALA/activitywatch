import time
import sys
import argparse
from datetime import datetime
from .config import ShipperConfig
from .outbox import SQLiteOutbox
from .redaction import RedactionEngine
from .aw_client import AWLocalClient
from .shipper import HTTPShipper

def run_sync_cycle(config: ShipperConfig, outbox: SQLiteOutbox, aw_client: AWLocalClient, redaction: RedactionEngine, shipper: HTTPShipper):
    # 1. Discovers local buckets
    buckets = aw_client.get_buckets()
    target_bucket_prefixes = ["aw-watcher-window", "aw-watcher-afk", "aw-watcher-web", "aw-watcher-vscode"]

    for b_id, b_meta in buckets.items():
        if not any(b_id.startswith(prefix) for prefix in target_bucket_prefixes):
            continue

        cursor = outbox.get_cursor(b_id, overlap_minutes=config.overlap_window_minutes)
        events = aw_client.get_events(b_id, start_time=cursor)

        if events:
            # Apply local redaction
            cleaned_events = [redaction.scrub_event(e) for e in events]
            outbox.enqueue_batch(config.device_id, b_id, cleaned_events)

            # Update bucket cursor to latest timestamp
            latest_time = max(datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00")) for e in events)
            outbox.update_cursor(b_id, latest_time)

    # 2. Flush pending outbox batches over HTTPS
    shipper.flush_outbox()

    # 3. Send heartbeat
    shipper.send_heartbeat()

def main():
    parser = argparse.ArgumentParser(description="ActivityWatch Enterprise Edge Shipper Daemon")
    parser.add_argument("--once", action="store_true", help="Run a single sync pass and exit")
    parser.add_argument("--device-id", type=str, help="Override device ID")
    parser.add_argument("--server-url", type=str, help="Central Ingest API URL")
    args = parser.parse_args()

    config = ShipperConfig()
    if args.device_id:
        config.device_id = args.device_id
    if args.server_url:
        config.server_url = args.server_url

    outbox = SQLiteOutbox(config.sqlite_db_path)
    redaction = RedactionEngine(config.redaction_patterns)
    aw_client = AWLocalClient(config.aw_server_url)
    shipper = HTTPShipper(config, outbox)

    print(f"[*] ActivityWatch Shipper started. Device ID: {config.device_id}")
    print(f"[*] Forwarding to: {config.server_url} (Sync interval: {config.sync_interval_seconds}s)")

    if args.once:
        run_sync_cycle(config, outbox, aw_client, redaction, shipper)
        print("[+] Single sync cycle completed.")
        return

    try:
        while True:
            run_sync_cycle(config, outbox, aw_client, redaction, shipper)
            time.sleep(config.sync_interval_seconds)
    except KeyboardInterrupt:
        print("\n[!] Shipper stopped by user.")

if __name__ == "__main__":
    main()
