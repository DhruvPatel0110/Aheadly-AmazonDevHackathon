"""
Data Models and Enums for Deadline Rescue.
Provides strong type-safety, validation, and JSON schemas for SQLite persistence
and MCP tool contracts.
"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class SourceType(str, Enum):
    EMAIL = "email"
    PDF = "pdf"
    SMS = "sms"
    RECEIPT = "receipt"
    MANUAL = "manual"


class DeadlineCategory(str, Enum):
    SUBSCRIPTION = "subscription"
    INSURANCE = "insurance"
    BROADBAND = "broadband"
    MOBILE = "mobile"
    UTILITY = "utility"
    DTH = "dth"
    RETURN_WINDOW = "return_window"
    OTHER = "other"


class ObligationType(str, Enum):
    PAYMENT_DUE = "payment_due"
    RENEWAL = "renewal"
    TRIAL_ENDING = "trial_ending"
    VALIDITY_EXPIRY = "validity_expiry"
    CANCELLATION_DEADLINE = "cancellation_deadline"
    RETURN_DEADLINE = "return_deadline"


class VerificationStatus(str, Enum):
    SOURCE_STATED = "source_stated"
    USER_CONFIRMED = "user_confirmed"
    ESTIMATED = "estimated"
    UNVERIFIED = "unverified"


class DeadlineStatus(str, Enum):
    NEEDS_REVIEW = "needs_review"
    CONFIRMED = "confirmed"
    UPCOMING = "upcoming"
    ACTION_NEEDED = "action_needed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DATE_UNVERIFIED = "date_unverified"
    DISMISSED = "dismissed"


class RecurrenceType(str, Enum):
    ONE_TIME = "one_time"
    MONTHLY = "monthly"
    ANNUAL = "annual"
    UNCONFIRMED = "unconfirmed"


class ReminderStatus(str, Enum):
    SCHEDULED = "scheduled"
    FIRED = "fired"
    DISMISSED = "dismissed"


def __getattr__(name: str):
    """Lazy import schemas to avoid circular dependencies while preserving backward compatibility."""
    import app.schemas as schemas
    if hasattr(schemas, name):
        return getattr(schemas, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

