import unittest
import os
import uuid
from datetime import datetime
from client.aw_shipper.outbox import SQLiteOutbox

class TestSQLiteOutbox(unittest.TestCase):
    def setUp(self):
        self.db_path = f"test_outbox_{uuid.uuid4().hex}.db"
        self.outbox = SQLiteOutbox(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except Exception:
                pass

    def test_cursor_with_sliding_overlap(self):
        bucket = "aw-watcher-window_laptop"
        now = datetime(2026, 11, 10, 14, 0, 0)
        self.outbox.update_cursor(bucket, now)

        # 10 minutes overlap should set cursor to 13:50
        cursor = self.outbox.get_cursor(bucket, overlap_minutes=10)
        self.assertIsNotNone(cursor)
        self.assertEqual(cursor.hour, 13)
        self.assertEqual(cursor.minute, 50)

    def test_enqueue_and_dequeue_batch(self):
        events = [{"id": 1, "timestamp": "2026-11-10T10:00:00Z", "duration": 10.0}]
        self.outbox.enqueue_batch("dev-01", "aw-watcher-window", events)

        batches = self.outbox.get_pending_batches(limit=10)
        self.assertEqual(len(batches), 1)
        self.assertEqual(batches[0]["payload"]["device_id"], "dev-01")

        self.outbox.remove_batch(batches[0]["id"])
        remaining = self.outbox.get_pending_batches(limit=10)
        self.assertEqual(len(remaining), 0)

if __name__ == "__main__":
    unittest.main()
