from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class WorkflowStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    TIMED_OUT = "TIMED_OUT"

@dataclass
class WorkflowRecord:
    workflow_id: str
    action: str
    requested_by: str
    context: dict[str, Any]
    status: WorkflowStatus
    created_at: datetime
    expires_at: datetime
    resolved_at: datetime | None = None
    resolved_by: str | None = None


class CreateWorkflowRequest(BaseModel):
    action: str
    requested_by: str
    context: dict[str, Any] = {}
    timeout_minutes: int = Field(default=30, ge=0)


class CreateWorkflowResponse(BaseModel):
    workflow_id: str
    status: WorkflowStatus
    expires_at: datetime


class ReviewRequest(BaseModel):
    reviewed_by: str


class WorkflowDetailResponse(BaseModel):
    workflow_id: str
    action: str
    requested_by: str
    context: dict[str, Any]
    status: WorkflowStatus
    created_at: datetime
    expires_at: datetime
    resolved_at: datetime | None
    resolved_by: str | None
