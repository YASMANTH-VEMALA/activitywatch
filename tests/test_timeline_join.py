import unittest
from datetime import datetime, timedelta
from server.workers.timeline_joiner import TimelineJoiner

class TestTimelineJoiner(unittest.TestCase):
    def test_canonical_event_schema(self):
        person_id = "test-person"
        t0 = datetime(2026, 11, 10, 9, 30, 0)

        activity_spans = [
            {
                "start_time": t0 + timedelta(minutes=10),
                "end_time": t0 + timedelta(minutes=40),
                "duration_seconds": 1800,
                "app_name": "VS Code",
                "window_title": "main.py",
                "is_afk": False,
                "category": "Development"
            }
        ]
        punches = [
            {
                "punch_type": "IN",
                "punch_time": t0,
                "device_identifier": "TURNSTILE-01",
                "location": "HQ Gate"
            }
        ]
        ai_logs = [
            {
                "request_id": "req-1",
                "model_name": "gpt-4o",
                "total_tokens": 800,
                "cost_usd": 0.005,
                "timestamp": t0 + timedelta(minutes=20)
            }
        ]

        unified = TimelineJoiner.join_events(person_id, activity_spans, punches, ai_logs)

        # Should have exactly 3 events
        self.assertEqual(len(unified), 3)

        # Sorted by timestamp ascending: punch (09:30), activity (09:40), AI call (09:50)
        self.assertEqual(unified[0]["source"], "biometric_punch")
        self.assertEqual(unified[1]["source"], "laptop_activity")
        self.assertEqual(unified[2]["source"], "ai_call")

        # Verify shared schema fields
        for ev in unified:
            self.assertIn("person_id", ev)
            self.assertIn("timestamp", ev)
            self.assertIn("end_timestamp", ev)
            self.assertIn("duration_seconds", ev)
            self.assertIn("source", ev)
            self.assertIn("category", ev)
            self.assertIn("summary", ev)
            self.assertIn("payload", ev)

if __name__ == "__main__":
    unittest.main()

