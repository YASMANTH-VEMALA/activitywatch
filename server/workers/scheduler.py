import asyncio
import logging
from datetime import datetime, date, timedelta, timezone
from db.memory_store import store
from workers.rule_engine import RuleEngine
from workers.metrics import MetricsCalculator

logger = logging.getLogger(__name__)

class BackgroundIntelligenceWorker:
    """
    Micro-batch scheduler that runs continuously:
    1. Evaluates rules R01, R02, R05, R07 against recent data.
    2. Recalculates day records and utilization metrics.
    3. Monitors device staleness (no ping in > 30 minutes).
    """

    def __init__(self, interval_seconds: int = 30):
        self.interval_seconds = interval_seconds
        self.is_running = False
        self.rule_engine = RuleEngine()

    async def start(self):
        self.is_running = True
        logger.info(f"Background Intelligence Worker started (interval: {self.interval_seconds}s)")
        while self.is_running:
            try:
                self.run_cycle()
            except Exception as e:
                logger.error(f"Error in intelligence worker cycle: {e}")
            await asyncio.sleep(self.interval_seconds)

    def stop(self):
        self.is_running = False
        logger.info("Background Intelligence Worker stopped.")

    def run_cycle(self):
        today = date.today()
        # 1. Evaluate rules across all people
        for p_id in store.people.keys():
            spans = [s for s in store.activity_spans if s["person_id"] == p_id and s["start_time"].date() == today]
            punches = [p for p in store.biometric_punches if p["person_id"] == p_id and p["punch_time"].date() == today]
            ai_logs = [a for a in store.ai_usage_logs if a["person_id"] == p_id and a["timestamp"].date() == today]

            flags = self.rule_engine.evaluate_day(p_id, today, punches, spans, ai_logs)

            existing_flag_keys = {
                (f["person_id"], f["rule_code"], str(f["target_date"]))
                for f in store.discrepancy_flags
            }

            for f in flags:
                key = (f["person_id"], f["rule_code"], str(f["target_date"]))
                if key not in existing_flag_keys:
                    store.discrepancy_flags.append(f)
                    existing_flag_keys.add(key)
                    logger.info(f"[!] Raised Discrepancy Flag: {f['rule_code']} ({f['title']}) for person {p_id}")

            # 2. Recalculate Day Records
            open_flags = [f for f in store.discrepancy_flags if f["person_id"] == p_id and f["status"] == "OPEN"]
            m = MetricsCalculator.calculate_day_metrics(p_id, today, punches, spans, ai_logs, len(open_flags))
            store.day_records[f"{p_id}_{today.isoformat()}"] = m

        # 3. Staleness Check
        now = datetime.now(timezone.utc)
        for d_id, dev in store.devices.items():
            last_hb_str = dev.get("last_heartbeat")
            if last_hb_str:
                try:
                    last_hb = datetime.fromisoformat(last_hb_str)
                    if (now - last_hb) > timedelta(minutes=30):
                        dev["is_stale"] = True
                    else:
                        dev["is_stale"] = False
                except Exception:
                    pass

