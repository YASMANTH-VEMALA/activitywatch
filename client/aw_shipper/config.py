import os
from dataclasses import dataclass, field
from typing import List

@dataclass
class ShipperConfig:
    server_url: str = os.getenv("INGEST_SERVER_URL", "http://localhost:8000/v1/ingest")
    heartbeat_url: str = os.getenv("HEARTBEAT_SERVER_URL", "http://localhost:8000/v1/heartbeat")
    device_id: str = os.getenv("AW_DEVICE_ID", "dev-pilot-laptop-01")
    device_key: str = os.getenv("AW_DEVICE_KEY", "pilot_secret_device_key_123")
    aw_server_url: str = os.getenv("AW_LOCAL_URL", "http://localhost:5600/api/0")
    sqlite_db_path: str = os.getenv("SQLITE_OUTBOX_PATH", "outbox.db")
    sync_interval_seconds: int = int(os.getenv("SYNC_INTERVAL_SEC", "120")) # 2 min
    overlap_window_minutes: int = int(os.getenv("OVERLAP_MINUTES", "10"))
    redaction_patterns: List[str] = field(default_factory=lambda: [
        r"(?i)password[=:]\s*\S+",
        r"(?i)bearer\s+[a-zA-Z0-9_\-\.]+",
        r"(?i)api[_-]?key[=:]\s*\S+",
        r"(?i)token[=:]\s*\S+",
        r"(?i)incognito",
        r"(?i)private browsing"
    ])
