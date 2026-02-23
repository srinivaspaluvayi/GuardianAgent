"""FastAPI: list pending approvals, approve/deny by id (MongoDB)."""
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException
from pymongo import ReturnDocument

from app.db import APPROVALS_COLLECTION, get_db
from app.models import ApprovalResponse, ApproveDenyBody

router = APIRouter(prefix="/approvals", tags=["approvals"])


def _doc_to_approval_response(doc: dict) -> ApprovalResponse:
    return ApprovalResponse(
        id=str(doc["_id"]),
        action_id=doc["action_id"],
        agent_id=doc["agent_id"],
        action_type=doc["action_type"],
        resource=doc.get("resource", ""),
        payload=doc.get("payload", {}),
        risk_score=doc.get("risk_score", 0.0),
        reason=doc.get("reason", ""),
        status=doc["status"],
        resolved_at=doc.get("resolved_at"),
        resolved_by=doc.get("resolved_by"),
        created_at=doc.get("created_at") or datetime.now(timezone.utc),
    )


def _parse_oid(approval_id: str) -> ObjectId:
    try:
        return ObjectId(approval_id)
    except InvalidId:
        raise HTTPException(status_code=404, detail="Approval not found")


@router.get("", response_model=list[ApprovalResponse])
async def list_approvals(
    status: str | None = None,
    db=Depends(get_db),
):
    """List approvals; optional filter by status (pending, approved, denied)."""
    query = {} if status is None else {"status": status}
    cursor = db[APPROVALS_COLLECTION].find(query).sort("created_at", -1)
    docs = await cursor.to_list(length=None)
    return [_doc_to_approval_response(d) for d in docs]


@router.get("/{approval_id}", response_model=ApprovalResponse)
async def get_approval(
    approval_id: str,
    db=Depends(get_db),
):
    oid = _parse_oid(approval_id)
    doc = await db[APPROVALS_COLLECTION].find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Approval not found")
    return _doc_to_approval_response(doc)


@router.post("/{approval_id}/approve", response_model=ApprovalResponse)
async def approve(
    approval_id: str,
    body: ApproveDenyBody | None = None,
    db=Depends(get_db),
):
    oid = _parse_oid(approval_id)
    now = datetime.now(timezone.utc)
    update = {"$set": {"status": "approved", "resolved_at": now, "resolved_by": (body.resolved_by if body else None) or "api"}}
    doc = await db[APPROVALS_COLLECTION].find_one_and_update(
        {"_id": oid, "status": "pending"},
        update,
        return_document=ReturnDocument.AFTER,
    )
    if not doc:
        existing = await db[APPROVALS_COLLECTION].find_one({"_id": oid})
        if not existing:
            raise HTTPException(status_code=404, detail="Approval not found")
        raise HTTPException(status_code=400, detail=f"Approval already {existing['status']}")
    return _doc_to_approval_response(doc)


@router.post("/{approval_id}/deny", response_model=ApprovalResponse)
async def deny(
    approval_id: str,
    body: ApproveDenyBody | None = None,
    db=Depends(get_db),
):
    oid = _parse_oid(approval_id)
    now = datetime.now(timezone.utc)
    update = {"$set": {"status": "denied", "resolved_at": now, "resolved_by": (body.resolved_by if body else None) or "api"}}
    doc = await db[APPROVALS_COLLECTION].find_one_and_update(
        {"_id": oid, "status": "pending"},
        update,
        return_document=ReturnDocument.AFTER,
    )
    if not doc:
        existing = await db[APPROVALS_COLLECTION].find_one({"_id": oid})
        if not existing:
            raise HTTPException(status_code=404, detail="Approval not found")
        raise HTTPException(status_code=400, detail=f"Approval already {existing['status']}")
    return _doc_to_approval_response(doc)
