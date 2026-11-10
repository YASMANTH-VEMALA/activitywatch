from fastapi import APIRouter, HTTPException
from datetime import datetime, date
from typing import Optional
import uuid
from db.memory_store import store
from ingest.models import BiometricPunchRequest, MockPunchGenerateRequest

router = APIRouter(prefix="/api/v1/punches", tags=["Biometric Punches"])

@router.post("")
async def record_punch(punch: BiometricPunchRequest):
    if punch.person_id not in store.people:
        raise HTTPException(status_code=404, detail="Person not found")

    record = {
        "punch_id": str(uuid.uuid4()),
        "person_id": punch.person_id,
        "punch_type": punch.punch_type,
        "punch_time": punch.punch_time,
        "device_identifier": punch.device_identifier,
        "location": punch.location,
        "is_mock": punch.is_mock
    }
    store.biometric_punches.append(record)

    return {
        "status": "success",
        "message": f"Biometric Punch {punch.punch_type} recorded.",
        "record": record
    }

@router.post("/mock-generate")
async def generate_mock_punches(req: MockPunchGenerateRequest):
    target = req.target_date or date.today()
    store.generate_pilot_scenarios(target)
    return {
        "status": "success",
        "message": f"Mock punches and pilot activity generated for {target.isoformat()}"
    }
