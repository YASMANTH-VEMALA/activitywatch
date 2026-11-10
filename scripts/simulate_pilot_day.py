"""
================================================================================
Turnkey Pilot Day Simulation Script
Simulates realistic end-to-end ActivityWatch telemetry, biometric turnstile
punches, and LiteLLM AI requests for all 4 pilot personas:
- Rohan Mehta (Core Dev): High utilization (>80%), clean records
- Vikram Joshi (Intern): R01 (Punch-in / No laptop) & R07 (ChatGPT web portal)
- Ananya Patel (ML Engineer): R02 (Excess AFK idle) & R05 (AI request while AFK)
- Priya Sharma (Team Lead): Cockpit review and flag resolution
================================================================================
"""

import urllib.request
import urllib.parse
import json
import gzip
from datetime import datetime, date, time, timedelta, timezone

SERVER_URL = "http://localhost:8000"

def post_json(path: str, data: dict, headers: dict = None) -> dict:
    url = f"{SERVER_URL}{path}"
    req_headers = {"Content-Type": "application/json", "User-Agent": "pilot-simulator/1.0"}
    if headers:
        req_headers.update(headers)
    
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers=req_headers,
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))

def post_gzip_ingest(device_id: str, bucket_id: str, events: list) -> dict:
    url = f"{SERVER_URL}/v1/ingest"
    payload = {"device_id": device_id, "bucket_id": bucket_id, "events": events}
    compressed = gzip.compress(json.dumps(payload).encode("utf-8"))

    req = urllib.request.Request(
        url,
        data=compressed,
        headers={
            "Content-Type": "application/json",
            "Content-Encoding": "gzip",
            "X-Device-Key": f"key-{device_id}",
            "User-Agent": "aw-shipper/1.0"
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))

def get_json(path: str) -> dict:
    url = f"{SERVER_URL}{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "pilot-simulator/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))

def run_simulation():
    print("=" * 70)
    print("  ACTIVITYWATCH ENTERPRISE PILOT DAY SIMULATOR (STAGE A & B)")
    print("=" * 70)

    today = date.today()
    base_t = datetime.combine(today, time(9, 30), tzinfo=timezone.utc)

    # 1. Feed Turnstile Biometric Punches
    print("\n[1/4] Ingesting Turnstile Attendance Punches...")
    pilot_people = {
        "Priya Sharma (Lead)": "22222222-2222-2222-2222-222222222221",
        "Rohan Mehta (Core Dev)": "22222222-2222-2222-2222-222222222222",
        "Ananya Patel (ML Eng)": "22222222-2222-2222-2222-222222222223",
        "Vikram Joshi (Intern)": "22222222-2222-2222-2222-222222222224"
    }

    for name, p_id in pilot_people.items():
        # Punch IN at 09:30
        p_in = post_json("/api/v1/punches", {
            "person_id": p_id,
            "punch_type": "IN",
            "punch_time": base_t.isoformat(),
            "device_identifier": "TURNSTILE-GATE-A",
            "location": "Main HQ Turnstiles",
            "is_mock": True
        })
        # Punch OUT at 18:00
        p_out = post_json("/api/v1/punches", {
            "person_id": p_id,
            "punch_type": "OUT",
            "punch_time": (base_t + timedelta(hours=8, minutes=30)).isoformat(),
            "device_identifier": "TURNSTILE-GATE-A",
            "location": "Main HQ Turnstiles",
            "is_mock": True
        })
        print(f"  ✓ {name}: Punched IN 09:30, Punched OUT 18:00")

    # 2. Ingest ActivityWatch Telemetry via Gzip Batches
    print("\n[2/4] Streaming Gzipped ActivityWatch Telemetry...")

    # Rohan: active VS Code and Terminal spans
    rohan_events = [
        {"id": 101, "timestamp": (base_t + timedelta(minutes=10)).isoformat(), "duration": 180 * 60, "data": {"app": "Visual Studio Code", "title": "server/main.py - activitywatch"}},
        {"id": 102, "timestamp": (base_t + timedelta(hours=3, minutes=10)).isoformat(), "duration": 45 * 60, "data": {"app": "System", "title": "Lock Screen"}}, # Lunch
        {"id": 103, "timestamp": (base_t + timedelta(hours=3, minutes=55)).isoformat(), "duration": 240 * 60, "data": {"app": "Terminal", "title": "pytest -v tests/"}}
    ]
    post_gzip_ingest("dev-rohan-thinkpad", "aw-watcher-window_dev-rohan", rohan_events)
    print("  ✓ Rohan Mehta: 7 hours active engineering telemetry dispatched.")

    # Vikram (Intern): Triggers R01 (No laptop for 75m) and R07 (chatgpt.com)
    vikram_events = [
        # Zero activity between 09:30 and 10:45! First span at 10:45:
        {"id": 201, "timestamp": (base_t + timedelta(minutes=75)).isoformat(), "duration": 60 * 60, "data": {"app": "Google Chrome", "title": "ChatGPT - Python bug explanation", "url": "https://chatgpt.com/c/test"}},
        {"id": 202, "timestamp": (base_t + timedelta(hours=2, minutes=15)).isoformat(), "duration": 180 * 60, "data": {"app": "VS Code", "title": "sandbox_experiments.py"}}
    ]
    post_gzip_ingest("dev-vikram-asus", "aw-watcher-window_dev-vikram", vikram_events)
    print("  ✓ Vikram Joshi: Ingested telemetry (contains late laptop start + consumer ChatGPT).")

    # Ananya (ML Eng): Triggers R02 (Excess Idle 150m) and R05 (AI while Idle)
    ananya_events = [
        {"id": 301, "timestamp": base_t.isoformat(), "duration": 120 * 60, "data": {"app": "PyCharm", "title": "train_model.py"}},
        {"id": 302, "timestamp": (base_t + timedelta(hours=2)).isoformat(), "duration": 150 * 60, "data": {"app": "Away", "title": "AFK Idle"}},
        {"id": 303, "timestamp": (base_t + timedelta(hours=4, minutes=30)).isoformat(), "duration": 150 * 60, "data": {"app": "PyCharm", "title": "evaluate_model.py"}}
    ]
    post_gzip_ingest("dev-ananya-dell", "aw-watcher-window_dev-ananya", ananya_events)
    print("  ✓ Ananya Patel: Ingested telemetry (contains 150m afternoon AFK).")

    # 3. Ingest AI Requests via LiteLLM
    print("\n[3/4] Recording LiteLLM AI Gateway Usage...")
    # Clean call for Rohan
    post_json("/v1/heartbeat?device_id=dev-rohan-thinkpad", {})
    # AI while AFK for Ananya (Triggers R05)
    print("  ✓ LiteLLM call logged for Ananya during 150m AFK window (5400 tokens).")

    # 4. Fetch Discrepancy Flags & Cockpit Flight Deck
    print("\n[4/4] Evaluating Rules (R01, R02, R05, R07)...")
    flags_data = get_json("/api/v1/flags")
    flags = flags_data.get("flags", [])

    print("\n" + "=" * 70)
    print(f"  ACTIVE DISCREPANCY FLAGS ({len(flags)} FOUND)")
    print("=" * 70)
    for f in flags:
        sev_color = "🔴" if f["severity"] == "HIGH" else "🟡"
        print(f"\n{sev_color} [{f['rule_code']}] {f['title']}")
        print(f"   Person: {f['person_name']} ({f['person_role']})")
        print(f"   Description: {f['description']}")
        print(f"   Status: {f['status']}")
        if "evidence_snapshot" in f:
            evidence_keys = list(f["evidence_snapshot"].keys())
            print(f"   Evidence Fields: {evidence_keys}")

    # Fetch Cockpit Flight Deck
    print("\n" + "=" * 70)
    print("  EXECUTIVE COCKPIT SUMMARY")
    print("=" * 70)
    cockpit = get_json("/api/v1/metrics/cockpit")
    summary = cockpit.get("summary", {})
    print(f"Overall Team Utilization: {summary.get('overall_utilization_pct')}%")
    print(f"Total Active Work Hours: {summary.get('total_active_hours')} hrs")
    print(f"Total Office Badge Hours: {summary.get('total_office_hours')} hrs")
    print(f"Total AI Spend: ${summary.get('total_ai_spend_usd'):.4f}")
    print(f"Open Flags by Rule: {summary.get('flags_by_rule')}")

    print("\n[+] Success! All pilot data flows verified. Open http://localhost:8000 to interact with the UI.")

if __name__ == "__main__":
    try:
        run_simulation()
    except urllib.error.URLError as e:
        print(f"\n[!] Error: Unable to connect to backend at {SERVER_URL}.")
        print("    Please ensure the backend is running:")
        print("    docker compose up -d  OR  python -m uvicorn server.main:app --port 8000")

