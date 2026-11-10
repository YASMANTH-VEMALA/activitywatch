from datetime import datetime, date
from typing import List, Dict, Any, Optional

class MetricsCalculator:
    """
    Computes daily performance and attendance metrics:
    - Office Hours (from first punch-in to last punch-out)
    - Active Laptop Hours (non-AFK)
    - Idle Hours (AFK)
    - AI Spend & Tokens
    - Utilization Percentage (Active Hours / Office Hours)
    """

    @staticmethod
    def calculate_day_metrics(
        person_id: str,
        work_date: date,
        punches: List[Dict[str, Any]],
        activity_spans: List[Dict[str, Any]],
        ai_logs: List[Dict[str, Any]],
        open_flags_count: int = 0
    ) -> Dict[str, Any]:
        in_punches = [p for p in punches if p.get("punch_type") == "IN"]
        out_punches = [p for p in punches if p.get("punch_type") == "OUT"]

        first_in = min([p["punch_time"] for p in in_punches]) if in_punches else None
        last_out = max([p["punch_time"] for p in out_punches]) if out_punches else None

        office_hours = 8.0
        if first_in and last_out and first_in < last_out:
            office_hours = (last_out - first_in).total_seconds() / 3600.0

        active_seconds = sum(
            s["duration_seconds"] for s in activity_spans if not s.get("is_afk", False)
        )
        idle_seconds = sum(
            s["duration_seconds"] for s in activity_spans if s.get("is_afk", False)
        )

        active_hours = active_seconds / 3600.0
        idle_hours = idle_seconds / 3600.0

        ai_spend = sum(a.get("cost_usd", 0.0) for a in ai_logs)
        ai_tokens = sum(a.get("total_tokens", 0) for a in ai_logs)
        # Approximate 3 minutes of mental engagement per AI interaction
        ai_time_minutes = min(active_hours * 60.0, len(ai_logs) * 3.0)

        utilization = 0.0
        if office_hours > 0:
            utilization = round(min(100.0, (active_hours / office_hours) * 100.0), 1)

        return {
            "person_id": person_id,
            "work_date": work_date,
            "first_punch_in": first_in,
            "last_punch_out": last_out,
            "office_hours": round(office_hours, 2),
            "active_hours": round(active_hours, 2),
            "idle_hours": round(idle_hours, 2),
            "ai_time_minutes": round(ai_time_minutes, 1),
            "ai_spend_usd": round(ai_spend, 4),
            "ai_tokens_count": ai_tokens,
            "utilization_percentage": utilization,
            "open_flags_count": open_flags_count
        }

