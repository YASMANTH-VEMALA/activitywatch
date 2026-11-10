import csv
import os
import glob
from datetime import datetime, date, time, timedelta
from typing import List, Dict, Any, Optional
import uuid
import logging

logger = logging.getLogger(__name__)

class BiometricConnector:
    """
    Biometric Attendance Connector supporting:
    1. Clean mock punch generation with anomaly simulation
    2. CSV punch file ingestion (from physical biometric badge scanners)
    3. Webhook payload parsing
    """

    @staticmethod
    def parse_csv_punches(csv_file_path: str) -> List[Dict[str, Any]]:
        """
        Parses standard turnstile export CSV format:
        Columns: employee_email_or_id, timestamp, punch_type (IN/OUT), device_id, location
        """
        punches = []
        if not os.path.exists(csv_file_path):
            return punches

        with open(csv_file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    ts = datetime.fromisoformat(row["timestamp"])
                    punch_type = row["punch_type"].strip().upper()
                    if punch_type not in ("IN", "OUT"):
                        continue
                    punches.append({
                        "punch_id": str(uuid.uuid4()),
                        "person_identifier": row.get("employee_email_or_id", "").strip(),
                        "punch_type": punch_type,
                        "punch_time": ts,
                        "device_identifier": row.get("device_id", "TURNSTILE-01").strip(),
                        "location": row.get("location", "Main Office").strip(),
                        "is_mock": False
                    })
                except Exception as e:
                    logger.warning(f"Skipping malformed row in {csv_file_path}: {row} ({e})")
        return punches

    @staticmethod
    def generate_day_punches(
        person_id: str,
        target_date: date,
        punch_in_time: time = time(9, 30),
        punch_out_time: time = time(18, 30),
        device: str = "TURNSTILE-01",
        location: str = "HQ Gate A"
    ) -> List[Dict[str, Any]]:
        in_dt = datetime.combine(target_date, punch_in_time)
        out_dt = datetime.combine(target_date, punch_out_time)

        return [
            {
                "punch_id": str(uuid.uuid4()),
                "person_id": person_id,
                "punch_type": "IN",
                "punch_time": in_dt,
                "device_identifier": device,
                "location": location,
                "is_mock": True
            },
            {
                "punch_id": str(uuid.uuid4()),
                "person_id": person_id,
                "punch_type": "OUT",
                "punch_time": out_dt,
                "device_identifier": device,
                "location": location,
                "is_mock": True
            }
        ]

