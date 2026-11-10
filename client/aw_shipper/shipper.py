import urllib.request
import gzip
import json
from typing import Dict, Any
from .config import ShipperConfig
from .outbox import SQLiteOutbox

class HTTPShipper:
    """
    Dispatches gzip-compressed batches to the cloud ingest endpoint
    with device key authentication.
    """

    def __init__(self, config: ShipperConfig, outbox: SQLiteOutbox):
        self.config = config
        self.outbox = outbox

    def send_batch(self, payload: Dict[str, Any]) -> bool:
        json_bytes = json.dumps(payload).encode("utf-8")
        compressed = gzip.compress(json_bytes)

        req = urllib.request.Request(
            self.config.server_url,
            data=compressed,
            headers={
                "Content-Type": "application/json",
                "Content-Encoding": "gzip",
                "X-Device-Key": self.config.device_key,
                "ngrok-skip-browser-warning": "true",
                "User-Agent": "aw-shipper/1.0"
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status in (200, 201)
        except Exception as e:
            return False

    def send_heartbeat(self) -> bool:
        url = f"{self.config.heartbeat_url}?device_id={self.config.device_id}"
        req = urllib.request.Request(
            url,
            headers={
                "X-Device-Key": self.config.device_key,
                "ngrok-skip-browser-warning": "true",
                "User-Agent": "aw-shipper/1.0"
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status in (200, 204)
        except Exception:
            return False

    def flush_outbox(self) -> int:
        sent_count = 0
        while True:
            pending = self.outbox.get_pending_batches(limit=10)
            if not pending:
                break
            for item in pending:
                success = self.send_batch(item["payload"])
                if success:
                    self.outbox.remove_batch(item["id"])
                    events_count = len(item["payload"].get("events", []))
                    sent_count += events_count
                    print(f"  [✓] Forwarded batch #{item['id']} ({events_count} events to central platform)")
                else:
                    self.outbox.increment_retry(item["id"])
                    print(f"  [!] Failed to forward batch #{item['id']}, will retry...")
                    return sent_count
        return sent_count

