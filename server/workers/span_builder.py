import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

UNAPPROVED_AI_DOMAINS = [
    "chatgpt.com",
    "chat.openai.com",
    "claude.ai",
    "deepseek.com",
    "poe.com",
    "perplexity.ai"
]

def extract_domain(url_or_title: Optional[str]) -> Optional[str]:
    if not url_or_title:
        return None
    if url_or_title.startswith("http://") or url_or_title.startswith("https://"):
        try:
            return urlparse(url_or_title).netloc.lower()
        except Exception:
            pass
    # Regex fallback for domain-like strings
    match = re.search(r'([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', url_or_title)
    if match:
        return match.group(1).lower()
    return None

def is_unapproved_ai_domain(domain_or_title: Optional[str]) -> bool:
    if not domain_or_title:
        return False
    lower = domain_or_title.lower()
    return any(unapproved in lower for unapproved in UNAPPROVED_AI_DOMAINS)

class SpanBuilder:
    """
    Normalizes ActivityWatch raw events:
    Merges window focus, browser tab details, and AFK state into clean activity spans.
    """

    @staticmethod
    def build_spans_from_events(
        person_id: str,
        device_id: str,
        window_events: List[Dict[str, Any]],
        afk_events: List[Dict[str, Any]],
        web_events: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        spans = []
        web_events = web_events or []

        # Map afk intervals
        afk_intervals = []
        for e in afk_events:
            ts = e["timestamp"]
            dur = e.get("duration", 0.0)
            status = e.get("data", {}).get("status", "not-afk")
            end_ts = ts + timedelta(seconds=dur)
            afk_intervals.append({
                "start": ts,
                "end": end_ts,
                "is_afk": status == "afk"
            })

        for w in window_events:
            start_time = w["timestamp"]
            duration = w.get("duration", 0.0)
            if duration <= 0.0:
                continue
            end_time = start_time + timedelta(seconds=duration)
            app_name = w.get("data", {}).get("app", "Unknown")
            window_title = w.get("data", {}).get("title", "")

            # Match associated web event if browser
            matched_url = None
            matched_domain = None
            if any(b in app_name.lower() for b in ["chrome", "edge", "firefox", "brave", "safari"]):
                for web in web_events:
                    w_ts = web["timestamp"]
                    if abs((w_ts - start_time).total_seconds()) < 10:
                        matched_url = web.get("data", {}).get("url")
                        matched_domain = extract_domain(matched_url)
                        break

            if not matched_domain:
                matched_domain = extract_domain(window_title)

            # Check if this span intersected with AFK
            is_afk = False
            for afk in afk_intervals:
                if afk["is_afk"] and max(start_time, afk["start"]) < min(end_time, afk["end"]):
                    is_afk = True
                    break

            unapproved = is_unapproved_ai_domain(matched_domain) or is_unapproved_ai_domain(window_title)

            category = "Development" if any(k in app_name.lower() for k in ["code", "terminal", "idea", "pycharm", "git"]) else "General"
            if unapproved:
                category = "Unapproved AI Tool"

            spans.append({
                "person_id": person_id,
                "device_id": device_id,
                "start_time": start_time,
                "end_time": end_time,
                "duration_seconds": duration,
                "app_name": app_name,
                "window_title": window_title,
                "url": matched_url,
                "url_domain": matched_domain,
                "is_afk": is_afk,
                "is_unapproved_ai": unapproved,
                "category": category
            })

        return spans
