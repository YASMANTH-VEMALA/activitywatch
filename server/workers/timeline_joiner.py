from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
import uuid

class TimelineJoiner:
    """
    Joins disparate source records (activity spans, biometric punches, AI calls)
    into a single canonical timeline adhering to the shared event schema:
    (person_id, timestamp, end_timestamp, duration_seconds, source, category, summary, payload)
    """

    @staticmethod
    def join_events(
        person_id: str,
        activity_spans: List[Dict[str, Any]],
        punches: List[Dict[str, Any]],
        ai_logs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        unified = []

        # 1. Biometric Punches
        for p in punches:
            punch_type = p["punch_type"]
            ts = p["punch_time"]
            loc = p.get("location", "Main Office")
            dev = p.get("device_identifier", "Turnstile")
            unified.append({
                "event_id": str(p.get("punch_id", uuid.uuid4())),
                "person_id": person_id,
                "timestamp": ts,
                "end_timestamp": ts + timedelta(seconds=60), # 1-minute visual pin
                "duration_seconds": 60.0,
                "source": "biometric_punch",
                "category": "Attendance",
                "summary": f"Biometric Punch {punch_type} ({dev} - {loc})",
                "payload": {
                    "punch_type": punch_type,
                    "device": dev,
                    "location": loc,
                    "is_mock": p.get("is_mock", False)
                }
            })

        # 2. Activity Spans
        for s in activity_spans:
            app = s.get("app_name", "App")
            title = s.get("window_title", "")
            is_afk = s.get("is_afk", False)
            cat = s.get("category", "Work")
            if is_afk:
                summary = f"Idle / AFK ({app})"
                cat = "Idle"
            else:
                summary = f"{app}: {title[:60]}" if title else app

            unified.append({
                "event_id": str(uuid.uuid4()),
                "person_id": person_id,
                "timestamp": s["start_time"],
                "end_timestamp": s["end_time"],
                "duration_seconds": s["duration_seconds"],
                "source": "laptop_activity",
                "category": cat,
                "summary": summary,
                "payload": {
                    "app_name": app,
                    "window_title": title,
                    "url": s.get("url"),
                    "domain": s.get("url_domain"),
                    "is_afk": is_afk,
                    "is_unapproved_ai": s.get("is_unapproved_ai", False)
                }
            })

        # 3. AI Usage Logs (LiteLLM)
        for a in ai_logs:
            model = a.get("model_name", "AI Model")
            tokens = a.get("total_tokens", 0)
            cost = a.get("cost_usd", 0.0)
            req_id = a.get("request_id", "")
            ts = a.get("timestamp", datetime.now(timezone.utc))
            approved = a.get("is_approved_tool", True)

            cat = "AI Generation" if approved else "Unapproved AI Tool"
            summary = f"LiteLLM: {model} ({tokens} tokens, ${cost:.4f})"

            unified.append({
                "event_id": str(uuid.uuid4()),
                "person_id": person_id,
                "timestamp": ts,
                "end_timestamp": ts + timedelta(seconds=120), # marker
                "duration_seconds": 120.0,
                "source": "ai_call",
                "category": cat,
                "summary": summary,
                "payload": {
                    "request_id": req_id,
                    "model": model,
                    "tokens": tokens,
                    "cost_usd": cost,
                    "is_approved": approved,
                    "trace_id": a.get("langfuse_trace_id")
                }
            })

        # Sort strictly by timestamp ascending
        unified.sort(key=lambda x: x["timestamp"])
        return unified
