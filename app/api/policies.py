"""FastAPI CRUD for policy rules (MongoDB)."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.db import POLICIES_COLLECTION, get_db
from app.models import PolicyCreate, PolicyResponse

router = APIRouter(prefix="/policies", tags=["policies"])


def _doc_to_policy_response(doc: dict) -> PolicyResponse:
    return PolicyResponse(
        id=str(doc["_id"]),
        name=doc["name"],
        kind=doc["kind"],
        definition=doc["definition"],
        version=doc.get("version", 1),
        created_at=doc.get("created_at") or datetime.now(timezone.utc),
    )


@router.get("", response_model=list[PolicyResponse])
async def list_policies(db=Depends(get_db)):
    cursor = db[POLICIES_COLLECTION].find({}).sort("_id", 1)
    docs = await cursor.to_list(length=None)
    return [_doc_to_policy_response(d) for d in docs]


@router.post("", response_model=PolicyResponse, status_code=201)
async def create_policy(body: PolicyCreate, db=Depends(get_db)):
    now = datetime.now(timezone.utc)
    doc = {
        "name": body.name,
        "kind": body.kind,
        "definition": body.definition,
        "version": 1,
        "created_at": now,
    }
    result = await db[POLICIES_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _doc_to_policy_response(doc)
