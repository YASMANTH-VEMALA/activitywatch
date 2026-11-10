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
                "User-Agent": "aw-shipper/1.0"
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status in (200, 204)
        except Exception:
            return False

    def flush_outbox(self):
        pending = self.outbox.get_pending_batches(limit=10)
        for item in pending:
            success = self.send_batch(item["payload"])
            if success:
                self.outbox.remove_batch(item["id"])
            else:
                self.outbox.increment_retry(item["id"])
                break # Stop processing queue until network connectivity is restored
