"""
Pydantic Schemas for API Requests, Responses, and MCP Tool Contracts.
Separates API payload representations from underlying database entities.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from app.models import (
    SourceType,
    DeadlineCategory,
    ObligationType,
    VerificationStatus,
    DeadlineStatus,
    RecurrenceType,
    ReminderStatus,
)


# ---------------------------------------------------------------------------
# Source Schemas
# ---------------------------------------------------------------------------

class SourceBase(BaseModel):
    title: str = Field(..., description="Document or message title / filename")
    raw_text: str = Field(..., description="Full extracted text content")
    source_type: SourceType = Field(default=SourceType.MANUAL)
    file_hash: Optional[str] = Field(None, description="SHA-256 hash to prevent duplicate ingestion")


class SourceCreate(SourceBase):
    pass


class Source(SourceBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: str
    duplicate: bool = False


# ---------------------------------------------------------------------------
# Deadline Schemas
# ---------------------------------------------------------------------------

class DeadlineBase(BaseModel):
    provider_name: str = Field(..., description="Name of company or service provider (e.g. Netflix, Airtel)")
    category: DeadlineCategory = Field(default=DeadlineCategory.OTHER)
    obligation_type: ObligationType = Field(default=ObligationType.PAYMENT_DUE)
    candidate_date: str = Field(..., description="Extracted ISO date (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)")
    original_date_str: Optional[str] = Field(None, description="Exact date string found in the source")
    amount: Optional[float] = Field(None, description="Payment amount if explicitly stated")
    currency: str = Field(default="INR", description="Currency code (e.g., INR, USD)")
    evidence_snippet: str = Field(..., description="Verbatim quote from the source supporting the date")
    evidence_char_start: Optional[int] = Field(None, description="Character start index in source text")
    evidence_char_end: Optional[int] = Field(None, description="Character end index in source text")
    extraction_confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    verification_status: VerificationStatus = Field(default=VerificationStatus.SOURCE_STATED)
    recurrence: RecurrenceType = Field(default=RecurrenceType.UNCONFIRMED)
    official_url: Optional[str] = Field(None, description="Verified provider action URL")
    next_step_instructions: Optional[str] = Field(None, description="Actionable guidance or cancellation checklist")
    status: DeadlineStatus = Field(default=DeadlineStatus.NEEDS_REVIEW)
    owner: Optional[str] = Field("Self", description="Assigned task owner")


class DeadlineCreate(DeadlineBase):
    source_id: str


class DeadlineUpdate(BaseModel):
    provider_name: Optional[str] = None
    category: Optional[DeadlineCategory] = None
    obligation_type: Optional[ObligationType] = None
    candidate_date: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    verification_status: Optional[VerificationStatus] = None
    recurrence: Optional[RecurrenceType] = None
    official_url: Optional[str] = None
    next_step_instructions: Optional[str] = None
    status: Optional[DeadlineStatus] = None
    owner: Optional[str] = None
    resolution_notes: Optional[str] = None


class Deadline(DeadlineBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_id: str
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# Reminder Schemas
# ---------------------------------------------------------------------------

class ReminderCreate(BaseModel):
    deadline_id: str
    remind_at: str
    lead_days: int = 1


class Reminder(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    deadline_id: str
    remind_at: str
    lead_days: int
    status: ReminderStatus
    created_at: str


# ---------------------------------------------------------------------------
# Audit Log Schemas
# ---------------------------------------------------------------------------

class AuditLog(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    deadline_id: str
    action: str
    previous_value: Optional[str] = None
    new_value: Optional[str] = None
    timestamp: str


# ---------------------------------------------------------------------------
# Conversational Agent Schemas
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    active_deadline_id: Optional[str] = None
