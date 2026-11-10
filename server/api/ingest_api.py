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
        # Check if primary live laptop exists, else create one for this device
        person_id = "live-laptop-01"
        if person_id in store.people:
            store.people[person_id]["full_name"] = f"My Laptop ({batch.device_id})"
        else:
            store.people[person_id] = {
                "person_id": person_id,
                "email": f"{batch.device_id}@pilot.local",
                "full_name": f"My Laptop ({batch.device_id})",
                "role": "Active User",
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

    inserted = 0
    raw_window_events = []
    raw_afk_events = []
    raw_web_events = []

    for ev in batch.events:
        item = {
            "device_id": batch.device_id,
            "bucket_id": batch.bucket_id,
            "aw_event_id": ev.id,
            "timestamp": ev.timestamp,
            "duration": ev.duration,
            "data": ev.data
        }
        store.raw_events.append(item)
        inserted += 1

        if "window" in batch.bucket_id:
            raw_window_events.append(item)
        elif "afk" in batch.bucket_id:
            raw_afk_events.append(item)
        elif "web" in batch.bucket_id:
            raw_web_events.append(item)

    # Immediately build normalized spans if window events exist
    if raw_window_events:
        new_spans = SpanBuilder.build_spans_from_events(
            person_id=device["person_id"],
            device_id=batch.device_id,
            window_events=raw_window_events,
            afk_events=raw_afk_events,
            web_events=raw_web_events
        )
        store.activity_spans.extend(new_spans)

    return IngestResponse(
        status="success",
        device_id=batch.device_id,
        bucket_id=batch.bucket_id,
        received_count=len(batch.events),
        inserted_count=inserted
    )

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

