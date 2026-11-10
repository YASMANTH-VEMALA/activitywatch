from datetime import datetime, date
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field

# ActivityWatch Ingest Models
class RawAWEvent(BaseModel):
    id: int = Field(..., alias="aw_event_id")
    timestamp: datetime
    duration: float = Field(0.0, description="Duration in seconds")
    data: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        populate_by_name = True

class BatchIngestRequest(BaseModel):
    device_id: str
    bucket_id: str
    events: List[RawAWEvent]

class IngestResponse(BaseModel):
    status: str = "success"
    device_id: str
    bucket_id: str
    received_count: int
    inserted_count: int

# Biometric Punch Models
class BiometricPunchRequest(BaseModel):
    person_id: str
    punch_type: Literal["IN", "OUT"]
    punch_time: datetime
    device_identifier: str = "TURNSTILE-01"
    location: str = "Main Office HQ"
    is_mock: bool = False

class MockPunchGenerateRequest(BaseModel):
    target_date: Optional[date] = None
    simulate_anomalies: bool = True  # Generate cases for R01, R02, etc.

# AI Gateway & LiteLLM Usage Models
class AIUsageLogRequest(BaseModel):
    request_id: str
    person_id: str
    project_id: Optional[str] = None
    model_name: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    is_approved_tool: bool = True
    langfuse_trace_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

# Discrepancy Flag Resolution Model
class FlagResolutionRequest(BaseModel):
    status: Literal["ACCEPTED", "REJECTED", "EXPLAINED"]
    resolution_notes: str
    resolved_by: Optional[str] = None

# Day End Update Form Models
class DayEndSubmitRequest(BaseModel):
    person_id: str
    work_date: date
    accomplishments: str
    blockers: Optional[str] = None
    project_allocations: List[Dict[str, Any]] = Field(default_factory=list)

# Consent Sign Request
class ConsentSignRequest(BaseModel):
    person_id: str
    policy_version: str = "v1.0-pilot"

