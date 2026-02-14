"""Approvals API: list pending, approve, deny."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import get_settings
from app.db import get_db
from app.db_models import Approval, Decision
from app.streams.redis_streams import RedisStreams

router = APIRouter(prefix="/approvals", tags=["approvals"])


class ApproveRequest(BaseModel):
    reviewer_id: Optional[str] = None
    comment: Optional[str] = None


class DenyRequest(BaseModel):
    reviewer_id: Optional[str] = None
    comment: Optional[str] = None


class ApprovalItem(BaseModel):
    request_id: str
    intent_event_id: str
    decision_event_id: Optional[str]
    status: str
    reviewer_id: Optional[str]
    comment: Optional[str]
    created_at: datetime
    resolved_at: Optional[datetime]


@router.get("/pending", response_model=List[ApprovalItem])
def list_pending():
    with get_db() as session:
        rows = (
            session.query(Approval)
            .filter(Approval.status == "PENDING")
            .order_by(Approval.created_at.desc())
            .all()
        )
        return [
            ApprovalItem(
                request_id=r.request_id,
                intent_event_id=r.intent_event_id,
                decision_event_id=r.decision_event_id,
                status=r.status,
                reviewer_id=r.reviewer_id,
                comment=r.comment,
                created_at=r.created_at,
                resolved_at=r.resolved_at,
            )
            for r in rows
        ]


@router.post("/{approval_id}/approve")
def approve(approval_id: str, body: ApproveRequest):
    try:
        UUID(approval_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid approval id")
    with get_db() as session:
        approval = session.query(Approval).filter(Approval.request_id == approval_id).first()
        if not approval:
            raise HTTPException(status_code=404, detail="Approval not found")
        if approval.status != "PENDING":
            raise HTTPException(status_code=400, detail=f"Approval already {approval.status}")
        approval.status = "APPROVED"
        approval.reviewer_id = body.reviewer_id
        approval.comment = body.comment
        approval.resolved_at = datetime.now(timezone.utc)
        session.flush()
    _emit_approval_decision(approval_id, "APPROVED", body.comment)
    return {"status": "APPROVED", "request_id": approval_id}


@router.post("/{approval_id}/deny")
def deny(approval_id: str, body: DenyRequest):
    try:
        UUID(approval_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid approval id")
    with get_db() as session:
        approval = session.query(Approval).filter(Approval.request_id == approval_id).first()
        if not approval:
            raise HTTPException(status_code=404, detail="Approval not found")
        if approval.status != "PENDING":
            raise HTTPException(status_code=400, detail=f"Approval already {approval.status}")
        approval.status = "DENIED"
        approval.reviewer_id = body.reviewer_id
        approval.comment = body.comment
        approval.resolved_at = datetime.now(timezone.utc)
        session.flush()
    _emit_approval_decision(approval_id, "DENIED", body.comment)
    return {"status": "DENIED", "request_id": approval_id}


def _emit_approval_decision(request_id: str, decision: str, comment: Optional[str]) -> None:
    settings = get_settings()
    bus = RedisStreams(settings.redis_url)
    bus.xadd(
        settings.stream_approval_decision,
        {
            "request_id": request_id,
            "decision": decision,
            "comment": comment or "",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
