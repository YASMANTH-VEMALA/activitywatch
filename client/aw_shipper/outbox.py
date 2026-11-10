import sqlite3
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

class SQLiteOutbox:
    """
    Manages local offline queuing and bucket cursor tracking on the laptop.
    Ensures zero data loss if network connection drops.
    """

    def __init__(self, db_path: str = "outbox.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cursors (
                    bucket_id TEXT PRIMARY KEY,
                    last_synced_time TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS outbox_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    bucket_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    retry_count INTEGER DEFAULT 0
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def get_cursor(self, bucket_id: str, overlap_minutes: int = 10) -> Optional[datetime]:
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute("SELECT last_synced_time FROM cursors WHERE bucket_id = ?", (bucket_id,))
            row = cur.fetchone()
            if row:
                last_dt = datetime.fromisoformat(row[0])
                # Subtract sliding overlap window to catch retroactive heartbeat merges
                return last_dt - timedelta(minutes=overlap_minutes)
            return None
        finally:
            conn.close()

    def update_cursor(self, bucket_id: str, latest_event_time: datetime):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                INSERT INTO cursors (bucket_id, last_synced_time) 
                VALUES (?, ?)
                ON CONFLICT(bucket_id) DO UPDATE SET last_synced_time = excluded.last_synced_time
            """, (bucket_id, latest_event_time.isoformat()))
            conn.commit()
        finally:
            conn.close()

    def enqueue_batch(self, device_id: str, bucket_id: str, events: List[Dict[str, Any]]):
        if not events:
            return
        payload = json.dumps({"device_id": device_id, "bucket_id": bucket_id, "events": events})
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                INSERT INTO outbox_queue (device_id, bucket_id, payload_json, created_at)
                VALUES (?, ?, ?, ?)
            """, (device_id, bucket_id, payload, datetime.now(timezone.utc).isoformat()))
            conn.commit()
        finally:
            conn.close()

    def get_pending_batches(self, limit: int = 20) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, payload_json, retry_count FROM outbox_queue ORDER BY id ASC LIMIT ?", (limit,))
            rows = cur.fetchall()
            batches = []
            for r in rows:
                batches.append({
                    "id": r[0],
                    "payload": json.loads(r[1]),
                    "retry_count": r[2]
                })
            return batches
        finally:
            conn.close()

    def remove_batch(self, batch_id: int):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("DELETE FROM outbox_queue WHERE id = ?", (batch_id,))
            conn.commit()
        finally:
            conn.close()

    def increment_retry(self, batch_id: int):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("UPDATE outbox_queue SET retry_count = retry_count + 1 WHERE id = ?", (batch_id,))
            conn.commit()
        finally:
            conn.close()
