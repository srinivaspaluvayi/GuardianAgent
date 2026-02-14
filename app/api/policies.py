"""Policies CRUD API."""
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db import get_db
from app.db_models import Policy as PolicyModel

router = APIRouter(prefix="/policies", tags=["policies"])


class PolicyCreate(BaseModel):
    policy_id: str
    version: int = 1
    priority: int = 0
    enabled: bool = True
    policy_jsonb: Dict[str, Any]


class PolicyItem(BaseModel):
    id: int
    policy_id: str
    version: int
    priority: int
    enabled: bool
    policy_jsonb: Dict[str, Any]

    class Config:
        from_attributes = True


@router.get("", response_model=List[PolicyItem])
def list_policies():
    with get_db() as session:
        rows = session.query(PolicyModel).order_by(PolicyModel.priority.desc()).all()
        return [
            PolicyItem(
                id=r.id,
                policy_id=r.policy_id,
                version=r.version,
                priority=r.priority,
                enabled=r.enabled,
                policy_jsonb=r.policy_jsonb,
            )
            for r in rows
        ]


@router.post("", response_model=PolicyItem, status_code=201)
def create_policy(body: PolicyCreate):
    with get_db() as session:
        existing = session.query(PolicyModel).filter(PolicyModel.policy_id == body.policy_id).first()
        if existing:
            raise HTTPException(status_code=409, detail="policy_id already exists")
        row = PolicyModel(
            policy_id=body.policy_id,
            version=body.version,
            priority=body.priority,
            enabled=body.enabled,
            policy_jsonb=body.policy_jsonb,
        )
        session.add(row)
        session.flush()
        session.refresh(row)
        return PolicyItem(
            id=row.id,
            policy_id=row.policy_id,
            version=row.version,
            priority=row.priority,
            enabled=row.enabled,
            policy_jsonb=row.policy_jsonb,
        )


@router.get("/{policy_id}", response_model=PolicyItem)
def get_policy(policy_id: str):
    with get_db() as session:
        row = session.query(PolicyModel).filter(PolicyModel.policy_id == policy_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="Policy not found")
        return PolicyItem(
            id=row.id,
            policy_id=row.policy_id,
            version=row.version,
            priority=row.priority,
            enabled=row.enabled,
            policy_jsonb=row.policy_jsonb,
        )


@router.delete("/{policy_id}", status_code=204)
def delete_policy(policy_id: str):
    with get_db() as session:
        row = session.query(PolicyModel).filter(PolicyModel.policy_id == policy_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="Policy not found")
        session.delete(row)
    return None
