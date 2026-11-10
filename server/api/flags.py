from fastapi import APIRouter, HTTPException, Query
from datetime import date, datetime
from typing import Optional, List
from db.memory_store import store
from ingest.models import FlagResolutionRequest
from workers.rule_engine import RuleEngine

router = APIRouter(prefix="/api/v1/flags", tags=["Discrepancies & Flags"])

@router.get("")
async def list_flags(
    status: Optional[str] = Query(None, description="Filter by status: OPEN, ACCEPTED, REJECTED, EXPLAINED"),
    rule: Optional[str] = Query(None, description="Filter by rule: R01, R02, R05, R07"),
    person_id: Optional[str] = Query(None)
):
    # Ensure rules are evaluated for all pilot users
    evaluate_flags_for_all()

    results = []
    for f in store.discrepancy_flags:
        if status and f["status"].upper() != status.upper():
            continue
        if rule and f["rule_code"].upper() != rule.upper():
            continue
        if person_id and f["person_id"] != person_id:
            continue
        
        person_info = store.people.get(f["person_id"], {})
        item = dict(f)
        item["person_name"] = person_info.get("full_name", "Unknown")
        item["person_role"] = person_info.get("role", "Unknown")
        results.append(item)

    return {
        "count": len(results),
        "flags": results
    }

@router.get("/{flag_id}")
async def get_flag_details(flag_id: str):
    for f in store.discrepancy_flags:
        if f["flag_id"] == flag_id:
            person_info = store.people.get(f["person_id"], {})
            return {
                "flag": f,
                "person": person_info
            }
    raise HTTPException(status_code=404, detail="Discrepancy flag not found")

@router.get("/{flag_id}/evidence")
async def get_flag_evidence(flag_id: str):
    for f in store.discrepancy_flags:
        if f["flag_id"] == flag_id:
            return {
                "flag_id": flag_id,
                "rule_code": f["rule_code"],
                "title": f["title"],
                "target_date": f["target_date"].isoformat() if hasattr(f["target_date"], "isoformat") else str(f["target_date"]),
                "evidence": f.get("evidence_snapshot", {})
            }
    raise HTTPException(status_code=404, detail="Discrepancy flag not found")

@router.post("/{flag_id}/resolve")
async def resolve_flag(flag_id: str, req: FlagResolutionRequest):
    for f in store.discrepancy_flags:
        if f["flag_id"] == flag_id:
            f["status"] = req.status
            f["resolution_notes"] = req.resolution_notes
            f["resolved_by"] = req.resolved_by or "Team Lead"
            f["resolved_at"] = datetime.utcnow().isoformat()
            return {
                "status": "success",
                "message": f"Flag {flag_id} resolved as {req.status}",
                "flag": f
            }
    raise HTTPException(status_code=404, detail="Discrepancy flag not found")

def evaluate_flags_for_all(target_date: Optional[date] = None):
    engine = RuleEngine()
    eval_date = target_date or date.today()

    existing_keys = {
        (f["person_id"], f["rule_code"], str(f["target_date"]))
        for f in store.discrepancy_flags
    }

    for p_id in store.people.keys():
        spans = [s for s in store.activity_spans if s["person_id"] == p_id and s["start_time"].date() == eval_date]
        punches = [p for p in store.biometric_punches if p["person_id"] == p_id and p["punch_time"].date() == eval_date]
        ai_logs = [a for a in store.ai_usage_logs if a["person_id"] == p_id and a["timestamp"].date() == eval_date]

        detected = engine.evaluate_day(p_id, eval_date, punches, spans, ai_logs)
        for flag in detected:
            key = (flag["person_id"], flag["rule_code"], str(flag["target_date"]))
            if key not in existing_keys:
                store.discrepancy_flags.append(flag)
                existing_keys.add(key)

