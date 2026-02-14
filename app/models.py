"""Pydantic event schemas for Guardian."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

DecisionType = Literal["ALLOW", "REWRITE", "BLOCK", "REQUIRE_APPROVAL"]
Severity = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class ActionModel(BaseModel):
    type: str
    tool: str
    target: str
    method: Optional[str] = None
    args: Dict[str, Any] = Field(default_factory=dict)


class ContextModel(BaseModel):
    user_prompt: Optional[str] = None
    model_output_excerpt: Optional[str] = None
    data_classification: List[str] = Field(default_factory=list)
    workspace: Optional[str] = None
    user_role: Optional[str] = None
    attachments: List[Dict[str, Any]] = Field(default_factory=list)


class ActionIntentEvent(BaseModel):
    event_id: str
    trace_id: str
    timestamp: datetime
    agent_id: str
    session_id: str
    user_id: str
    action: ActionModel
    context: ContextModel


class RiskModel(BaseModel):
    score: float
    severity: Severity
    reasons: List[str] = Field(default_factory=list)


class ApprovalModel(BaseModel):
    required: bool = False
    request_id: Optional[str] = None


class ActionDecisionEvent(BaseModel):
    event_id: str
    trace_id: str
    intent_event_id: str
    timestamp: datetime
    decision: DecisionType
    risk: RiskModel
    policy_hits: List[str] = Field(default_factory=list)
    rewrite: Optional[Dict[str, Any]] = None
    approval: ApprovalModel = Field(default_factory=ApprovalModel)
