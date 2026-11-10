from fastapi import APIRouter, HTTPException, Header, Request
from datetime import datetime
import gzip
import json
from typing import Optional
from db.memory_store import store
from ingest.models import BatchIngestRequest, IngestResponse
from workers.span_builder import SpanBuilder

router = APIRouter(tags=["Ingestion"])

@router.post("/v1/ingest", response_model=IngestResponse)
async def ingest_activitywatch_events(
    request: Request,
    x_device_key: Optional[str] = Header(None, alias="X-Device-Key")
):
    # Support gzip decompressed body if Content-Encoding is gzip
    body_bytes = await request.body()
    if request.headers.get("content-encoding") == "gzip":
        try:
            body_bytes = gzip.decompress(body_bytes)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Gzip decompression failed: {e}")

    try:
        payload_data = json.loads(body_bytes.decode("utf-8"))
        batch = BatchIngestRequest(**payload_data)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid JSON payload: {e}")

    device = store.devices.get(batch.device_id)
    if not device:
        # Create dedicated person profile for each distinct physical device
        person_id = f"person-{batch.device_id}"
        store.people[person_id] = {
            "person_id": person_id,
            "email": f"{batch.device_id}@pilot.local",
            "full_name": f"Laptop ({batch.device_id})",
            "role": "Active Pilot User",
            "department": "Engineering",
            "manager_id": None
        }
        device = {
            "device_id": batch.device_id,
            "person_id": person_id,
            "device_name": batch.device_id,
            "last_heartbeat": datetime.utcnow().isoformat()
        }
        store.devices[batch.device_id] = device

    # Deduplicate raw events by (device_id, bucket_id, aw_event_id/timestamp)
    existing_event_keys = {
        (e["device_id"], e["bucket_id"], e.get("aw_event_id") or str(e["timestamp"]))
        for e in store.raw_events
        if e["device_id"] == batch.device_id
    }

    inserted = 0
    for ev in batch.events:
        event_key = (batch.device_id, batch.bucket_id, ev.id or str(ev.timestamp))
        if event_key not in existing_event_keys:
            item = {
                "device_id": batch.device_id,
                "bucket_id": batch.bucket_id,
                "aw_event_id": ev.id,
                "timestamp": ev.timestamp,
                "duration": ev.duration,
                "data": ev.data
            }
            store.raw_events.append(item)
            existing_event_keys.add(event_key)
            inserted += 1

    # Reconstruct normalized spans for this device from ALL accumulated raw events
    all_windows = [e for e in store.raw_events if e["device_id"] == batch.device_id and "window" in e["bucket_id"]]
    all_afks = [e for e in store.raw_events if e["device_id"] == batch.device_id and "afk" in e["bucket_id"]]
    all_webs = [e for e in store.raw_events if e["device_id"] == batch.device_id and "web" in e["bucket_id"]]

    if all_windows:
        reconstructed_spans = SpanBuilder.build_spans_from_events(
            person_id=device["person_id"],
            device_id=batch.device_id,
            window_events=all_windows,
            afk_events=all_afks,
            web_events=all_webs
        )
        # Replace existing spans for this device with the clean, deduplicated set
        store.activity_spans = [
            s for s in store.activity_spans if s.get("device_id") != batch.device_id
        ] + reconstructed_spans

    # Immediate flag evaluation for this person
    from api.flags import evaluate_flags_for_all
    evaluate_flags_for_all()

    return IngestResponse(
        status="success",
        device_id=batch.device_id,
        bucket_id=batch.bucket_id,
        received_count=len(batch.events),
        inserted_count=inserted
    )

@router.post("/api/v1/reset")
@router.get("/api/v1/reset")
async def reset_telemetry_store():
    """Wipes in-memory telemetry, spans, and duplicate events for a clean slate."""
    store.reset()
    return {"status": "success", "message": "Telemetry store reset successfully. Awaiting fresh events from edge laptops."}

@router.post("/v1/heartbeat")
async def device_heartbeat(
    device_id: str,
    x_device_key: Optional[str] = Header(None, alias="X-Device-Key")
):
    if device_id in store.devices:
        store.devices[device_id]["last_heartbeat"] = datetime.utcnow().isoformat()
    return {"status": "ok", "device_id": device_id, "timestamp": datetime.utcnow().isoformat()}

@router.get("/v1/models")
async def list_ai_models():
    """Exposes LiteLLM compatible models list for IDEs and clients."""
    return {
        "object": "list",
        "data": [
            {"id": "gpt-4o", "object": "model", "created": 1715500000, "owned_by": "openai"},
            {"id": "claude-3-5-sonnet", "object": "model", "created": 1715500000, "owned_by": "anthropic"},
            {"id": "gemini-1.5-pro", "object": "model", "created": 1715500000, "owned_by": "google"}
        ]
    }

