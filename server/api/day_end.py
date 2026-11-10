from fastapi import APIRouter, HTTPException, Query
from datetime import date, datetime
from typing import Optional, Dict
from collections import Counter
from db.memory_store import store
from ingest.models import DayEndSubmitRequest

router = APIRouter(prefix="/api/v1/day-end", tags=["Day-End Update"])

@router.get("/prefill/{person_id}")
async def get_day_end_prefill(
    person_id: str,
    target_date: Optional[date] = Query(default=None, alias="date")
):
    if person_id not in store.people:
        raise HTTPException(status_code=404, detail="Person not found")

    query_date = target_date or date.today()

    spans = [
        s for s in store.activity_spans 
        if s["person_id"] == person_id and s["start_time"].date() == query_date and not s.get("is_afk", False)
    ]
    ai_logs = [
        a for a in store.ai_usage_logs 
        if a["person_id"] == person_id and a["timestamp"].date() == query_date
    ]

    # Calculate app breakdown
    app_durations = Counter()
    for s in spans:
        app_durations[s.get("app_name", "App")] += s.get("duration_seconds", 0.0)

    top_apps = [
        {"app": app, "minutes": round(secs / 60.0, 1)}
        for app, secs in app_durations.most_common(5)
    ]

    # AI tools used
    ai_models = Counter(a.get("model_name", "AI") for a in ai_logs)
    total_tokens = sum(a.get("total_tokens", 0) for a in ai_logs)
    total_ai_spend = sum(a.get("cost_usd", 0.0) for a in ai_logs)

    total_active_hours = sum(app_durations.values()) / 3600.0

    # Formulate draft accomplishment
    primary_app = top_apps[0]["app"] if top_apps else "Engineering Work"
    draft_accomplishment = (
        f"Invested {total_active_hours:.1f} hours primarily focused on {primary_app}. "
        f"Executed {len(ai_logs)} AI-assisted queries across {dict(ai_models)} ({total_tokens} tokens)."
    )

    return {
        "person_id": person_id,
        "person_name": store.people[person_id]["full_name"],
        "date": query_date.isoformat(),
        "total_active_hours": round(total_active_hours, 2),
        "top_apps": top_apps,
        "ai_summary": {
            "total_requests": len(ai_logs),
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_ai_spend, 4),
            "models_used": dict(ai_models)
        },
        "suggested_prefill": {
            "accomplishments": draft_accomplishment,
            "blockers": "None noted from system events."
        }
    }

@router.post("/submit")
async def submit_day_end(req: DayEndSubmitRequest):
    if req.person_id not in store.people:
        raise HTTPException(status_code=404, detail="Person not found")

    key = f"{req.person_id}_{req.work_date.isoformat()}"
    store.day_end_updates[key] = {
        "person_id": req.person_id,
        "work_date": req.work_date.isoformat(),
        "accomplishments": req.accomplishments,
        "blockers": req.blockers,
        "project_allocations": req.project_allocations,
        "submitted_at": datetime.utcnow().isoformat()
    }

    return {
        "status": "success",
        "message": f"Day-end update submitted successfully for {req.work_date.isoformat()}",
        "record": store.day_end_updates[key]
    }
