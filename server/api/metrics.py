from fastapi import APIRouter, HTTPException, Request
from datetime import date, datetime
from typing import Optional
from collections import Counter
from db.memory_store import store
from ingest.models import ConsentSignRequest
from workers.metrics import MetricsCalculator
from api.flags import evaluate_flags_for_all

router = APIRouter(prefix="/api/v1", tags=["Metrics & Cockpit"])

@router.get("/metrics/cockpit")
async def get_cockpit_metrics(target_date: Optional[date] = None):
    query_date = target_date or date.today()
    evaluate_flags_for_all(query_date)

    team_metrics = []
    total_active_hours = 0.0
    total_office_hours = 0.0
    total_ai_spend = 0.0

    for p_id, person in store.people.items():
        spans = [s for s in store.activity_spans if s["person_id"] == p_id and s["start_time"].date() == query_date]
        punches = [p for p in store.biometric_punches if p["person_id"] == p_id and p["punch_time"].date() == query_date]
        ai_logs = [a for a in store.ai_usage_logs if a["person_id"] == p_id and a["timestamp"].date() == query_date]
        
        person_flags = [f for f in store.discrepancy_flags if f["person_id"] == p_id and f["status"] == "OPEN"]

        m = MetricsCalculator.calculate_day_metrics(
            person_id=p_id,
            work_date=query_date,
            punches=punches,
            activity_spans=spans,
            ai_logs=ai_logs,
            open_flags_count=len(person_flags)
        )
        m["person_name"] = person["full_name"]
        m["role"] = person["role"]
        m["department"] = person["department"]
        team_metrics.append(m)

        total_active_hours += m["active_hours"]
        total_office_hours += m["office_hours"]
        total_ai_spend += m["ai_spend_usd"]

    overall_utilization = round((total_active_hours / max(0.1, total_office_hours)) * 100.0, 1)

    # Flags breakdown by rule
    open_flags = [f for f in store.discrepancy_flags if f["status"] == "OPEN"]
    rule_counts = Counter(f["rule_code"] for f in open_flags)

    return {
        "date": query_date.isoformat(),
        "summary": {
            "overall_utilization_pct": overall_utilization,
            "total_active_hours": round(total_active_hours, 1),
            "total_office_hours": round(total_office_hours, 1),
            "total_ai_spend_usd": round(total_ai_spend, 4),
            "total_open_flags": len(open_flags),
            "flags_by_rule": dict(rule_counts)
        },
        "team_metrics": team_metrics
    }

@router.post("/consent")
async def record_consent(req: ConsentSignRequest, request: Request):
    if req.person_id not in store.people:
        raise HTTPException(status_code=404, detail="Person not found")

    client_ip = request.client.host if request.client else "127.0.0.1"
    entry = {
        "person_id": req.person_id,
        "policy_version": req.policy_version,
        "signed_at": datetime.utcnow().isoformat(),
        "ip_address": client_ip,
        "user_agent": request.headers.get("user-agent", "Unknown")
    }
    store.consent_logs.append(entry)

    return {
        "status": "success",
        "message": "Consent logged successfully.",
        "consent": entry
    }

@router.get("/consent/{person_id}")
async def check_consent(person_id: str):
    user_consent = [c for c in store.consent_logs if c["person_id"] == person_id]
    return {
        "person_id": person_id,
        "has_consented": len(user_consent) > 0,
        "latest_consent": user_consent[-1] if user_consent else None
    }
