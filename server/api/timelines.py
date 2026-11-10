from fastapi import APIRouter, HTTPException, Query
from datetime import date, datetime
from typing import Optional, Dict, Any, List
from collections import defaultdict
from db.memory_store import store
from workers.timeline_joiner import TimelineJoiner
from workers.metrics import MetricsCalculator

router = APIRouter(prefix="/api/v1/timelines", tags=["Timelines"])

def to_local_date(dt: datetime) -> date:
    if hasattr(dt, "tzinfo") and dt.tzinfo:
        try:
            return dt.astimezone().date()
        except Exception:
            return dt.date()
    return dt.date()

def format_seconds(seconds: float) -> str:
    total_secs = int(seconds)
    hours = total_secs // 3600
    minutes = (total_secs % 3600) // 60
    secs = total_secs % 60
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"

@router.get("/people/list")
async def list_available_people():
    """Returns dynamic list of all registered devices/people."""
    people_list = []
    for p_id, p in store.people.items():
        dev_name = next((d["device_name"] for d in store.devices.values() if d.get("person_id") == p_id), "Laptop")
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

    # Filter activity spans for person & local date
    spans = [
        s for s in store.activity_spans 
        if s["person_id"] == person_id and to_local_date(s["start_time"]) == query_date
    ]

    # Filter biometric punches
    punches = [
        p for p in store.biometric_punches 
        if p["person_id"] == person_id and to_local_date(p["punch_time"]) == query_date
    ]

    # Filter AI calls
    ai_logs = [
        a for a in store.ai_usage_logs 
        if a["person_id"] == person_id and to_local_date(a["timestamp"]) == query_date
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

    # Aggregate Top Applications (focus time, non-AFK)
    app_durations = defaultdict(float)
    title_durations = defaultdict(float)
    for s in spans:
        if not s.get("is_afk", False):
            app = s.get("app_name") or "Unknown"
            title = s.get("window_title") or "Unknown"
            dur = s.get("duration_seconds", 0.0)
            app_durations[app] += dur
            title_durations[title] += dur

    top_applications = [
        {"app": app, "duration_seconds": round(dur, 1), "formatted": format_seconds(dur)}
        for app, dur in sorted(app_durations.items(), key=lambda x: x[1], reverse=True)[:10]
    ]

    top_titles = [
        {"title": title, "duration_seconds": round(dur, 1), "formatted": format_seconds(dur)}
        for title, dur in sorted(title_durations.items(), key=lambda x: x[1], reverse=True)[:10]
    ]

    active_secs = sum(s["duration_seconds"] for s in spans if not s.get("is_afk", False))
    metrics["active_time_formatted"] = format_seconds(active_secs)

    return {
        "person": store.people[person_id],
        "date": query_date.isoformat(),
        "metrics": metrics,
        "top_applications": top_applications,
        "top_window_titles": top_titles,
        "event_count": len(unified_events),
        "events": unified_events
    }

