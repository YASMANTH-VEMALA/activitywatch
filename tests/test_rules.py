import unittest
from datetime import datetime, date, timedelta
from server.workers.rule_engine import RuleEngine

class TestRuleEngine(unittest.TestCase):
    def setUp(self):
        self.engine = RuleEngine()
        self.person_id = "test-person-001"
        self.today = date(2026, 11, 10)
        self.base_time = datetime(2026, 11, 10, 9, 30, 0)

    def test_rule_r01_punch_in_no_laptop(self):
        # Punched in at 09:30
        punches = [{"punch_type": "IN", "punch_time": self.base_time}]
        # No laptop spans at all during first 45 min
        activity_spans = [
            {
                "start_time": self.base_time + timedelta(minutes=60),
                "end_time": self.base_time + timedelta(minutes=120),
                "duration_seconds": 3600,
                "is_afk": False,
                "app_name": "VS Code"
            }
        ]
        flags = self.engine.evaluate_day(self.person_id, self.today, punches, activity_spans, [])
        r01_flags = [f for f in flags if f["rule_code"] == "R01"]
        self.assertEqual(len(r01_flags), 1)
        self.assertEqual(r01_flags[0]["severity"], "HIGH")
        self.assertIn("active_seconds_recorded", r01_flags[0]["evidence_snapshot"])

    def test_rule_r02_excess_idle(self):
        punches = [
            {"punch_type": "IN", "punch_time": self.base_time},
            {"punch_type": "OUT", "punch_time": self.base_time + timedelta(hours=8)}
        ]
        # 120 minutes of AFK (limit is 90)
        activity_spans = [
            {
                "start_time": self.base_time + timedelta(hours=2),
                "end_time": self.base_time + timedelta(hours=4),
                "duration_seconds": 7200,
                "is_afk": True,
                "app_name": "Lock Screen"
            }
        ]
        flags = self.engine.evaluate_day(self.person_id, self.today, punches, activity_spans, [])
        r02_flags = [f for f in flags if f["rule_code"] == "R02"]
        self.assertEqual(len(r02_flags), 1)
        self.assertEqual(r02_flags[0]["severity"], "MEDIUM")

    def test_rule_r05_ai_while_idle(self):
        # User is AFK from 11:00 to 12:00
        afk_start = self.base_time + timedelta(hours=1, minutes=30)
        afk_end = self.base_time + timedelta(hours=2, minutes=30)
        activity_spans = [
            {
                "start_time": afk_start,
                "end_time": afk_end,
                "duration_seconds": 3600,
                "is_afk": True,
                "app_name": "Away From Keyboard"
            }
        ]
        # AI call executed at 12:00 during that AFK span
        ai_logs = [
            {
                "request_id": "req-automated-123",
                "model_name": "gpt-4o",
                "total_tokens": 1500,
                "timestamp": afk_start + timedelta(minutes=30),
                "is_approved_tool": True
            }
        ]
        flags = self.engine.evaluate_day(self.person_id, self.today, [], activity_spans, ai_logs)
        r05_flags = [f for f in flags if f["rule_code"] == "R05"]
        self.assertEqual(len(r05_flags), 1)
        self.assertEqual(r05_flags[0]["severity"], "HIGH")
        self.assertIn("afk_span", r05_flags[0]["evidence_snapshot"])

    def test_rule_r07_unapproved_ai_tool(self):
        activity_spans = [
            {
                "start_time": self.base_time,
                "end_time": self.base_time + timedelta(minutes=30),
                "duration_seconds": 1800,
                "is_afk": False,
                "app_name": "Google Chrome",
                "window_title": "ChatGPT - Internal Code Review",
                "url_domain": "chatgpt.com",
                "is_unapproved_ai": True
            }
        ]
        flags = self.engine.evaluate_day(self.person_id, self.today, [], activity_spans, [])
        r07_flags = [f for f in flags if f["rule_code"] == "R07"]
        self.assertEqual(len(r07_flags), 1)
        self.assertEqual(r07_flags[0]["severity"], "MEDIUM")
        self.assertEqual(r07_flags[0]["evidence_snapshot"]["domain"], "chatgpt.com")

if __name__ == "__main__":
    unittest.main()
