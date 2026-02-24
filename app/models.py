"""Pydantic shapes for API and pipeline. No business logic."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# --- Approvals API ---
class ApprovalResponse(BaseModel):
    id: str  # MongoDB _id as string
    action_id: str
    agent_id: str
    action_type: str
    resource: str
    payload: dict[str, Any]
    risk_score: float
    reason: str
    status: str
    resolved_at: datetime | None
    resolved_by: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApproveDenyBody(BaseModel):
    comment: str | None = None
    resolved_by: str | None = None


# --- Policy API ---
class PolicyCreate(BaseModel):
    name: str
    kind: str  # allowlist, denylist, dsl
    definition: dict[str, Any]


class PolicyResponse(BaseModel):
    id: str  # MongoDB _id as string
    name: str
    kind: str
    definition: dict[str, Any]
    version: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Action / Decision ---
class Action(BaseModel):
    """Action proposed by a supervised agent."""
    action_id: str
    agent_id: str
    type: str  # e.g. read_file, http_request, send_email
    resource: str = ""  # path, URL, etc.
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime | None = None


class Decision(BaseModel):
    """Guardian decision for an action."""
    action_id: str
    decision: str  # allowed | blocked | needs_approval | rewritten
    reason: str = ""
    score: float = 0.0
    rewritten_payload: dict[str, Any] | None = None
    approval_id: str | None = None


class EvaluateResponse(BaseModel):
    """Response for POST /actions/evaluate (full pipeline)."""
    action_id: str
    policy_decision: str  # allowed | denied | unknown (from policy engine)
    decision: str  # allowed | blocked | needs_approval | rewritten
    reason: str = ""
    score: float = 0.0
    rewritten_payload: dict[str, Any] | None = None
    approval_id: str | None = None
