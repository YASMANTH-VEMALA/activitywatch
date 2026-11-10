from datetime import datetime, date, time, timedelta
from typing import Dict, List, Any, Optional
import uuid

class StateStore:
    """
    In-memory state store and data management service.
    Pre-populated with Stage A pilot users, projects, tracking policies,
    and mock events demonstrating R01, R02, R05, and R07.
    """

    def __init__(self):
        self.tracking_policies: Dict[str, Dict[str, Any]] = {}
        self.people: Dict[str, Dict[str, Any]] = {}
        self.projects: Dict[str, Dict[str, Any]] = {}
        self.project_members: List[Dict[str, Any]] = []
        self.ai_virtual_keys: Dict[str, Dict[str, Any]] = {}
        self.devices: Dict[str, Dict[str, Any]] = {}
        self.biometric_punches: List[Dict[str, Any]] = []
        self.raw_events: List[Dict[str, Any]] = []
        self.activity_spans: List[Dict[str, Any]] = []
        self.unified_timeline: List[Dict[str, Any]] = []
        self.ai_usage_logs: List[Dict[str, Any]] = []
        self.discrepancy_flags: List[Dict[str, Any]] = []
        self.day_records: Dict[str, Dict[str, Any]] = {}
        self.day_end_updates: Dict[str, Dict[str, Any]] = {}
        self.consent_logs: List[Dict[str, Any]] = []
        self._seed_pilot_state()

    def _seed_pilot_state(self):
        # 1. Default Policy
        policy_id = "11111111-1111-1111-1111-111111111111"
        self.tracking_policies[policy_id] = {
            "policy_id": policy_id,
            "policy_name": "Standard Pilot Engineering Policy",
            "punch_grace_minutes_r01": 45,
            "min_active_seconds_r01": 300,
            "max_idle_minutes_r02": 90,
            "single_idle_block_limit_r02": 45,
            "ai_idle_token_threshold_r05": 500,
            "approved_ai_tools": ["litellm", "internal-portal", "claude-team"]
        }

        # 2. Primary Live Laptop Profile (Will receive your real ActivityWatch data)
        primary_id = "live-laptop-01"
        self.people[primary_id] = {
            "person_id": primary_id,
            "email": "laptop@pilot.local",
            "full_name": "My Laptop (Live)",
            "role": "Active User",
            "department": "Engineering",
            "manager_id": None
        }

        # 3. Default Projects
        prj_apollo = "33333333-3333-3333-3333-333333333331"
        self.projects[prj_apollo] = {
            "project_id": prj_apollo,
            "name": "Apollo Core Engine",
            "code": "PRJ-APOLLO",
            "classification": "Serious",
            "description": "Primary Project",
            "monthly_budget_usd": 1000.00,
            "allotted_members": ["My Laptop (Live)"]
        }

        # Devices mapped to the live laptop
        self.devices["dev-pilot-laptop-01"] = {"device_id": "dev-pilot-laptop-01", "person_id": primary_id, "device_name": "My Laptop"}
        self.devices["laptop-01"] = {"device_id": "laptop-01", "person_id": primary_id, "device_name": "My Laptop"}

    def generate_pilot_scenarios(self, target_date: date):
        """
        Populates realistic activity, punches, AI usage and triggers rules R01, R02, R05, R07.
        """
        p_rohan = "22222222-2222-2222-2222-222222222222"
        p_ananya = "22222222-2222-2222-2222-222222222223"
        p_vikram = "22222222-2222-2222-2222-222222222224"

        self.people[p_rohan] = {"person_id": p_rohan, "email": "rohan@pilot.local", "full_name": "Rohan Mehta", "role": "employee", "department": "Engineering"}
        self.people[p_ananya] = {"person_id": p_ananya, "email": "ananya@pilot.local", "full_name": "Ananya Patel", "role": "employee", "department": "Engineering"}
        self.people[p_vikram] = {"person_id": p_vikram, "email": "vikram@pilot.local", "full_name": "Vikram Joshi", "role": "intern", "department": "Engineering"}

        base_dt = datetime.combine(target_date, time(9, 30))

        # ─────────────────────────────────────────────────────────────
        # Scenario 1: Rohan Mehta - High Productivity + Clean Punches
        # ─────────────────────────────────────────────────────────────
        self.biometric_punches.append({
            "punch_id": str(uuid.uuid4()), "person_id": p_rohan, "punch_type": "IN",
            "punch_time": base_dt, "device_identifier": "TURNSTILE-01", "location": "HQ Gate A", "is_mock": True
        })
        self.biometric_punches.append({
            "punch_id": str(uuid.uuid4()), "person_id": p_rohan, "punch_type": "OUT",
            "punch_time": base_dt + timedelta(hours=8, minutes=30), "device_identifier": "TURNSTILE-01", "location": "HQ Gate A", "is_mock": True
        })

        # Rohan spans (starts working 10m after punch-in)
        self.activity_spans.extend([
            {"person_id": p_rohan, "device_id": "dev-rohan-thinkpad", "start_time": base_dt + timedelta(minutes=10), "end_time": base_dt + timedelta(hours=3), "duration_seconds": 170 * 60, "app_name": "Visual Studio Code", "window_title": "activitywatch/server/main.py", "is_afk": False, "category": "Development"},
            {"person_id": p_rohan, "device_id": "dev-rohan-thinkpad", "start_time": base_dt + timedelta(hours=3), "end_time": base_dt + timedelta(hours=3, minutes=45), "duration_seconds": 45 * 60, "app_name": "Lunch Break", "window_title": "Lock Screen", "is_afk": True, "category": "Idle"},
            {"person_id": p_rohan, "device_id": "dev-rohan-thinkpad", "start_time": base_dt + timedelta(hours=3, minutes=45), "end_time": base_dt + timedelta(hours=7, minutes=30), "duration_seconds": 225 * 60, "app_name": "Terminal", "window_title": "docker compose up -d", "is_afk": False, "category": "Development"}
        ])

        # Rohan AI usage (via LiteLLM)
        self.ai_usage_logs.append({
            "request_id": f"req-{uuid.uuid4()}", "person_id": p_rohan, "project_id": "33333333-3333-3333-3333-333333333331",
            "timestamp": base_dt + timedelta(hours=2), "model_name": "gpt-4o", "prompt_tokens": 820, "completion_tokens": 450, "total_tokens": 1270, "cost_usd": 0.0095, "is_approved_tool": True
        })

        # ─────────────────────────────────────────────────────────────
        # Scenario 2: Vikram Joshi (Intern) - Triggers R01 & R07
        # - Punched in at 09:30, but no laptop activity until 10:45 (Triggers R01)
        # - Direct browser use of chatgpt.com (Triggers R07)
        # ─────────────────────────────────────────────────────────────
        self.biometric_punches.append({
            "punch_id": str(uuid.uuid4()), "person_id": p_vikram, "punch_type": "IN",
            "punch_time": base_dt, "device_identifier": "TURNSTILE-02", "location": "HQ Gate B", "is_mock": True
        })
        self.biometric_punches.append({
            "punch_id": str(uuid.uuid4()), "person_id": p_vikram, "punch_type": "OUT",
            "punch_time": base_dt + timedelta(hours=7), "device_identifier": "TURNSTILE-02", "location": "HQ Gate B", "is_mock": True
        })

        # First laptop activity at 10:45 (75m after punch!)
        self.activity_spans.extend([
            {"person_id": p_vikram, "device_id": "dev-vikram-asus", "start_time": base_dt + timedelta(minutes=75), "end_time": base_dt + timedelta(hours=3), "duration_seconds": 105 * 60, "app_name": "Google Chrome", "window_title": "ChatGPT - Python script bug fix", "url": "https://chatgpt.com/c/123", "url_domain": "chatgpt.com", "is_afk": False, "is_unapproved_ai": True, "category": "Unapproved AI Tool"},
            {"person_id": p_vikram, "device_id": "dev-vikram-asus", "start_time": base_dt + timedelta(hours=3), "end_time": base_dt + timedelta(hours=6), "duration_seconds": 180 * 60, "app_name": "VS Code", "window_title": "test_runner.py", "is_afk": False, "is_unapproved_ai": False, "category": "Development"}
        ])

        # ─────────────────────────────────────────────────────────────
        # Scenario 3: Ananya Patel - Triggers R02 (Excess Idle) & R05 (AI While Idle)
        # - 2.5 hours AFK during afternoon (Triggers R02)
        # - High-volume LiteLLM call initiated while laptop is in deep AFK (Triggers R05)
        # ─────────────────────────────────────────────────────────────
        self.biometric_punches.append({
            "punch_id": str(uuid.uuid4()), "person_id": p_ananya, "punch_type": "IN",
            "punch_time": base_dt, "device_identifier": "TURNSTILE-01", "location": "HQ Gate A", "is_mock": True
        })
        self.biometric_punches.append({
            "punch_id": str(uuid.uuid4()), "person_id": p_ananya, "punch_type": "OUT",
            "punch_time": base_dt + timedelta(hours=8), "device_identifier": "TURNSTILE-01", "location": "HQ Gate A", "is_mock": True
        })

        afk_start = base_dt + timedelta(hours=2, minutes=30)
        afk_end = base_dt + timedelta(hours=5) # 150 minutes idle!
        self.activity_spans.extend([
            {"person_id": p_ananya, "device_id": "dev-ananya-dell", "start_time": base_dt, "end_time": afk_start, "duration_seconds": 150 * 60, "app_name": "PyCharm", "window_title": "vector_indexer.py", "is_afk": False, "category": "Development"},
            {"person_id": p_ananya, "device_id": "dev-ananya-dell", "start_time": afk_start, "end_time": afk_end, "duration_seconds": 150 * 60, "app_name": "Idle", "window_title": "Away From Keyboard", "is_afk": True, "category": "Idle"},
            {"person_id": p_ananya, "device_id": "dev-ananya-dell", "start_time": afk_end, "end_time": base_dt + timedelta(hours=7, minutes=30), "duration_seconds": 150 * 60, "app_name": "PyCharm", "window_title": "query_embeddings.py", "is_afk": False, "category": "Development"}
        ])

        # AI call during AFK period (e.g. automated script)
        self.ai_usage_logs.append({
            "request_id": f"req-{uuid.uuid4()}", "person_id": p_ananya, "project_id": "33333333-3333-3333-3333-333333333332",
            "timestamp": afk_start + timedelta(minutes=45), "model_name": "claude-3-5-sonnet", "prompt_tokens": 4200, "completion_tokens": 1200, "total_tokens": 5400, "cost_usd": 0.038, "is_approved_tool": True
        })

# Global singleton state store
store = StateStore()

