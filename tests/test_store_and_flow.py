import unittest
from datetime import date
from server.db.memory_store import StateStore
from server.workers.rule_engine import RuleEngine
from server.workers.metrics import MetricsCalculator

class TestStoreAndFlow(unittest.TestCase):
    def setUp(self):
        self.store = StateStore()
        self.today = date.today()

    def test_pilot_people_and_projects(self):
        self.assertGreaterEqual(len(self.store.people), 1)
        self.assertIn("live-laptop-01", self.store.people)

    def test_pilot_scenarios_trigger_expected_rules(self):
        self.store.generate_pilot_scenarios(self.today)
        engine = RuleEngine()
        all_flags = []

        for p_id in self.store.people.keys():
            spans = [s for s in self.store.activity_spans if s["person_id"] == p_id and s["start_time"].date() == self.today]
            punches = [p for p in self.store.biometric_punches if p["person_id"] == p_id and p["punch_time"].date() == self.today]
            ai_logs = [a for a in self.store.ai_usage_logs if a["person_id"] == p_id and a["timestamp"].date() == self.today]

            flags = engine.evaluate_day(p_id, self.today, punches, spans, ai_logs)
            all_flags.extend(flags)

        rule_codes = {f["rule_code"] for f in all_flags}
        # Must catch all required rules: R01, R02, R05, R07
        self.assertIn("R01", rule_codes)
        self.assertIn("R02", rule_codes)
        self.assertIn("R05", rule_codes)
        self.assertIn("R07", rule_codes)

        # Check evidence attached to all flags
        for f in all_flags:
            self.assertIn("evidence_snapshot", f)
            self.assertTrue(len(f["evidence_snapshot"]) > 0)

    def test_rohan_clean_metrics_and_high_utilization(self):
        self.store.generate_pilot_scenarios(self.today)
        p_rohan = "22222222-2222-2222-2222-222222222222"
        spans = [s for s in self.store.activity_spans if s["person_id"] == p_rohan and s["start_time"].date() == self.today]
        punches = [p for p in self.store.biometric_punches if p["person_id"] == p_rohan and p["punch_time"].date() == self.today]
        ai_logs = [a for a in self.store.ai_usage_logs if a["person_id"] == p_rohan and a["timestamp"].date() == self.today]

        m = MetricsCalculator.calculate_day_metrics(p_rohan, self.today, punches, spans, ai_logs)
        self.assertGreater(m["active_hours"], 5.0)
        self.assertGreater(m["utilization_percentage"], 65.0)
        self.assertGreater(m["ai_spend_usd"], 0.0)

if __name__ == "__main__":
    unittest.main()

