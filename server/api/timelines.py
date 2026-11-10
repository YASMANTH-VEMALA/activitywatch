from fastapi import APIRouter, HTTPException, Query
from datetime import date, datetime
from typing import Optional
from db.memory_store import store
from workers.timeline_joiner import TimelineJoiner
from workers.metrics import MetricsCalculator

router = APIRouter(prefix="/api/v1/timelines", tags=["Timelines"])

@router.get("/people/list")
async def list_available_people():
    """Returns dynamic list of all registered devices/people."""
    people_list = []
    for p_id, p in store.people.items():
        # Find associated device
        dev_name = next((d["device_name"] for d in store.devices.values() if d.get("person_id") == p_id), "Unknown")
        people_list.append({
            "person_id": p_id,
            "full_name": p.get("full_name", p_id),
            "role": p.get("role", "User"),
            "device_name": dev_name
        })
    return {"people": people_list}

@router.get("/{person_id}")
async def get_person_timeline(
    person_id: str,
    target_date: Optional[date] = Query(default=None, alias="date")
):
    if person_id not in store.people:
        raise HTTPException(status_code=404, detail="Person not found")

    query_date = target_date or date.today()

    # Filter activity spans for person & date
    spans = [
        s for s in store.activity_spans 
        if s["person_id"] == person_id and s["start_time"].date() == query_date
    ]

    # Filter biometric punches
    punches = [
        p for p in store.biometric_punches 
        if p["person_id"] == person_id and p["punch_time"].date() == query_date
    ]

    # Filter AI calls
    ai_logs = [
        a for a in store.ai_usage_logs 
        if a["person_id"] == person_id and a["timestamp"].date() == query_date
    ]

    # Join into unified timeline
    unified_events = TimelineJoiner.join_events(person_id, spans, punches, ai_logs)

    # Compute daily metrics
    metrics = MetricsCalculator.calculate_day_metrics(
        person_id=person_id,
        work_date=query_date,
        punches=punches,
        activity_spans=spans,
        ai_logs=ai_logs
    )

    return {
        "person": store.people[person_id],
        "date": query_date.isoformat(),
        "metrics": metrics,
        "event_count": len(unified_events),
        "events": unified_events
    }

