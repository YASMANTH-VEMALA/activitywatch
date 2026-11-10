from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
import uuid

class RuleEngine:
    """
    Evaluates unified timeline and source records to detect discrepancies.
    Implements rules R01, R02, R05, R07 and constructs structured evidence snapshots.
    """

    def __init__(self, policy: Optional[Dict[str, Any]] = None):
        self.policy = policy or {
            "punch_grace_minutes_r01": 45,
            "min_active_seconds_r01": 300, # 5 min
            "max_idle_minutes_r02": 90,
            "single_idle_block_limit_r02": 45,
            "ai_idle_token_threshold_r05": 500
        }

    def evaluate_day(
        self,
        person_id: str,
        target_date: date,
        punches: List[Dict[str, Any]],
        activity_spans: List[Dict[str, Any]],
        ai_logs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        flags = []

        # Find first punch-in and last punch-out
        in_punches = [p for p in punches if p.get("punch_type") == "IN"]
        out_punches = [p for p in punches if p.get("punch_type") == "OUT"]

        first_in = min([p["punch_time"] for p in in_punches]) if in_punches else None
        last_out = max([p["punch_time"] for p in out_punches]) if out_punches else None

        # -------------------------------------------------------------
        # RULE R01: Punch-in / No Laptop
        # -------------------------------------------------------------
        if first_in:
            grace_period_end = first_in + timedelta(minutes=self.policy["punch_grace_minutes_r01"])
            
            # Sum active non-AFK seconds within the grace window
            active_seconds_in_grace = 0.0
            spans_in_grace = []
            for s in activity_spans:
                s_start = s["start_time"]
                s_end = s["end_time"]
                # Overlap check
                overlap_start = max(first_in, s_start)
                overlap_end = min(grace_period_end, s_end)
                if overlap_start < overlap_end:
                    dur = (overlap_end - overlap_start).total_seconds()
                    spans_in_grace.append({"app": s.get("app_name"), "duration": dur, "is_afk": s.get("is_afk", False)})
                    if not s.get("is_afk", False):
                        active_seconds_in_grace += dur

            if active_seconds_in_grace < self.policy["min_active_seconds_r01"]:
                flags.append({
                    "flag_id": str(uuid.uuid4()),
                    "person_id": person_id,
                    "rule_code": "R01",
                    "title": "Punch-in Without Active Workstation",
                    "description": (
                        f"Punched IN at {first_in.strftime('%H:%M:%S')}, but recorded only "
                        f"{active_seconds_in_grace / 60.0:.1f} minutes of active laptop use in the first "
                        f"{self.policy['punch_grace_minutes_r01']} minutes."
                    ),
                    "severity": "HIGH",
                    "status": "OPEN",
                    "target_date": target_date,
                    "evidence_snapshot": {
                        "rule": "R01",
                        "punch_in_time": first_in.isoformat(),
                        "grace_window_minutes": self.policy["punch_grace_minutes_r01"],
                        "active_seconds_recorded": round(active_seconds_in_grace, 1),
                        "required_active_seconds": self.policy["min_active_seconds_r01"],
                        "spans_detected": spans_in_grace
                    }
                })

        # -------------------------------------------------------------
        # RULE R02: Excess Idle
        # -------------------------------------------------------------
        if first_in and last_out and first_in < last_out:
            total_idle_seconds = 0.0
            long_idle_blocks = []
            
            for s in activity_spans:
                if s.get("is_afk", False):
                    # Intersect with office hours
                    o_start = max(first_in, s["start_time"])
                    o_end = min(last_out, s["end_time"])
                    if o_start < o_end:
                        dur = (o_end - o_start).total_seconds()
                        total_idle_seconds += dur
                        if dur >= (self.policy["single_idle_block_limit_r02"] * 60):
                            long_idle_blocks.append({
                                "start": o_start.isoformat(),
                                "end": o_end.isoformat(),
                                "duration_minutes": round(dur / 60.0, 1)
                            })

            total_idle_minutes = total_idle_seconds / 60.0
            if total_idle_minutes > self.policy["max_idle_minutes_r02"] or len(long_idle_blocks) > 0:
                flags.append({
                    "flag_id": str(uuid.uuid4()),
                    "person_id": person_id,
                    "rule_code": "R02",
                    "title": "Excess Workstation Idle Time",
                    "description": (
                        f"Cumulative idle time reached {total_idle_minutes:.1f} min (limit: {self.policy['max_idle_minutes_r02']} min) "
                        f"during punched hours, with {len(long_idle_blocks)} single block(s) exceeding {self.policy['single_idle_block_limit_r02']} min."
                    ),
                    "severity": "MEDIUM",
                    "status": "OPEN",
                    "target_date": target_date,
                    "evidence_snapshot": {
                        "rule": "R02",
                        "total_idle_minutes": round(total_idle_minutes, 1),
                        "max_allowed_idle_minutes": self.policy["max_idle_minutes_r02"],
                        "long_idle_blocks": long_idle_blocks,
                        "office_window": {"first_in": first_in.isoformat(), "last_out": last_out.isoformat()}
                    }
                })

        # -------------------------------------------------------------
        # RULE R05: AI While Idle
        # -------------------------------------------------------------
        for a in ai_logs:
            a_ts = a.get("timestamp")
            if not a_ts:
                continue
            # Check if this AI call occurred during a sustained AFK span (> 15m)
            for s in activity_spans:
                if s.get("is_afk", False) and s["duration_seconds"] >= 900: # 15 min AFK
                    if s["start_time"] <= a_ts <= s["end_time"]:
                        tokens = a.get("total_tokens", 0)
                        model = a.get("model_name", "Unknown")
                        flags.append({
                            "flag_id": str(uuid.uuid4()),
                            "person_id": person_id,
                            "rule_code": "R05",
                            "title": "Automated / Idle AI Request Executed",
                            "description": (
                                f"LiteLLM model '{model}' was invoked ({tokens} tokens) while laptop was in an unmonitored "
                                f"AFK idle state (>15 minutes absence)."
                            ),
                            "severity": "HIGH",
                            "status": "OPEN",
                            "target_date": target_date,
                            "evidence_snapshot": {
                                "rule": "R05",
                                "request_id": a.get("request_id"),
                                "model_name": model,
                                "tokens": tokens,
                                "ai_call_timestamp": a_ts.isoformat(),
                                "afk_span": {
                                    "start": s["start_time"].isoformat(),
                                    "end": s["end_time"].isoformat(),
                                    "duration_minutes": round(s["duration_seconds"] / 60.0, 1)
                                }
                            }
                        })
                        break

        # -------------------------------------------------------------
        # RULE R07: Unapproved AI Tool
        # -------------------------------------------------------------
        # 1. Check activity spans for blacklisted AI sites (ChatGPT, Claude web, etc.)
        unapproved_spans = [s for s in activity_spans if s.get("is_unapproved_ai", False)]
        if unapproved_spans:
            total_unapproved_seconds = sum(s.get("duration_seconds", 0) for s in unapproved_spans)
            first_span = unapproved_spans[0]
            detected_target = first_span.get("url_domain") or first_span.get("window_title") or first_span.get("app_name")
            flags.append({
                "flag_id": str(uuid.uuid4()),
                "person_id": person_id,
                "rule_code": "R07",
                "title": "Unapproved External AI Tool Accessed",
                "description": (
                    f"Detected access to unauthorized consumer AI portal '{detected_target}' "
                    f"for {total_unapproved_seconds / 60.0:.1f} minutes on application '{first_span.get('app_name')}'. "
                    f"Enterprise AI workflows must route via authorized LiteLLM proxy."
                ),
                "severity": "MEDIUM",
                "status": "OPEN",
                "target_date": target_date,
                "evidence_snapshot": {
                    "rule": "R07",
                    "total_duration_minutes": round(total_unapproved_seconds / 60.0, 1),
                    "app_name": first_span.get("app_name"),
                    "window_title": first_span.get("window_title"),
                    "url": first_span.get("url"),
                    "domain": first_span.get("url_domain"),
                    "first_seen_timestamp": first_span["start_time"].isoformat(),
                    "total_instances_count": len(unapproved_spans),
                    "instances": [
                        {
                            "app": s.get("app_name"),
                            "title": s.get("window_title"),
                            "duration_seconds": round(s.get("duration_seconds", 0), 1),
                            "timestamp": s["start_time"].isoformat()
                        }
                        for s in unapproved_spans[:10]
                    ]
                }
            })

        # 2. Check if any AI call was flagged as unapproved tool
        for a in ai_logs:
            if not a.get("is_approved_tool", True):
                flags.append({
                    "flag_id": str(uuid.uuid4()),
                    "person_id": person_id,
                    "rule_code": "R07",
                    "title": "Unapproved Model / Route Invoked on AI Proxy",
                    "description": f"AI call used unapproved model route: {a.get('model_name')}.",
                    "severity": "HIGH",
                    "status": "OPEN",
                    "target_date": target_date,
                    "evidence_snapshot": {
                        "rule": "R07",
                        "request_id": a.get("request_id"),
                        "model_name": a.get("model_name"),
                        "timestamp": a.get("timestamp").isoformat() if a.get("timestamp") else None
                    }
                })
                break

        return flags

