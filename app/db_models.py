"""SQLAlchemy models for Guardian (actions, decisions, approvals, policies)."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, Boolean, Integer
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db import Base


def _uuid():
    import uuid
    return str(uuid.uuid4())


class Action(Base):
    __tablename__ = "actions"
    __table_args__ = (Index("ix_actions_created", "created_at"),)

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    trace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    agent_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target: Mapped[str] = mapped_column(String(1024), nullable=False)
    args_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    context_jsonb: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    decisions: Mapped[List["Decision"]] = relationship("Decision", back_populates="action", foreign_keys="Decision.intent_event_id")


class Decision(Base):
    __tablename__ = "decisions"
    __table_args__ = (Index("ix_decisions_trace", "intent_event_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, default=_uuid)
    intent_event_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("actions.event_id"), nullable=False, index=True
    )
    decision: Mapped[str] = mapped_column(String(32), nullable=False)  # ALLOW, REWRITE, BLOCK, REQUIRE_APPROVAL
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    reasons_jsonb: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    policy_hits_jsonb: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    rewrite_jsonb: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    action: Mapped[Optional["Action"]] = relationship("Action", back_populates="decisions", foreign_keys=[intent_event_id])
    approval: Mapped[Optional["Approval"]] = relationship("Approval", back_populates="decision", uselist=False)


class Approval(Base):
    __tablename__ = "approvals"
    __table_args__ = (Index("ix_approvals_status", "status"),)

    request_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    intent_event_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    decision_event_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("decisions.event_id"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")  # PENDING, APPROVED, DENIED
    reviewer_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    decision: Mapped[Optional["Decision"]] = relationship("Decision", back_populates="approval")


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    policy_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    policy_jsonb: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
