"""Simple HTML UI for evaluating actions, policies, and approvals (no JavaScript)."""
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ReturnDocument

from app.db import APPROVALS_COLLECTION, POLICIES_COLLECTION, get_db
from app.models import Action
from app.pipeline import run_pipeline

router = APIRouter(prefix="/ui", tags=["ui"])

templates = Jinja2Templates(directory="app/ui/templates")


@router.get("/evaluate")
async def evaluate_form(request: Request):
    """Render empty form."""
    return templates.TemplateResponse(
        "evaluate.html",
        {
            "request": request,
            "result": None,
            "error": None,
            "action_id": "",
            "agent_id": "",
            "type": "",
            "resource": "",
            "payload": "{}",
        },
    )


@router.post("/evaluate")
async def evaluate_submit(
    request: Request,
    action_id: str = Form(...),
    agent_id: str = Form(...),
    type: str = Form(...),
    resource: str = Form(""),
    payload: str = Form("{}"),
    db=Depends(get_db),
):
    """Handle form submit: build Action in Python, run pipeline, render result."""
    try:
        payload_obj = json.loads(payload or "{}")
    except json.JSONDecodeError as e:
        return templates.TemplateResponse(
            "evaluate.html",
            {
                "request": request,
                "result": None,
                "error": f"Invalid JSON in payload: {e}",
                "action_id": action_id,
                "agent_id": agent_id,
                "type": type,
                "resource": resource,
                "payload": payload,
            },
        )

    action = Action(
        action_id=action_id,
        agent_id=agent_id,
        type=type,
        resource=resource or "",
        payload=payload_obj,
    )

    result = await run_pipeline(db, action)
    result_dict = result.model_dump(mode="json")

    return templates.TemplateResponse(
        "evaluate.html",
        {
            "request": request,
            "result": result_dict,
            "error": None,
            "action_id": action_id,
            "agent_id": agent_id,
            "type": type,
            "resource": resource,
            "payload": payload,
        },
    )


@router.get("/policies")
async def policies_form(request: Request, db=Depends(get_db)):
    """List existing policies and show create form."""
    cursor = db[POLICIES_COLLECTION].find({}).sort("_id", 1)
    docs = await cursor.to_list(length=None)
    policies: list[dict] = []
    for doc in docs:
        policies.append(
            {
                "id": str(doc.get("_id")),
                "name": doc.get("name", ""),
                "kind": doc.get("kind", ""),
                "version": doc.get("version", 1),
                "created_at": doc.get("created_at"),
            }
        )

    return templates.TemplateResponse(
        "policies.html",
        {
            "request": request,
            "policies": policies,
            "error": None,
            "name": "",
            "kind": "allowlist",
            "definition": '{\n  "rules": []\n}',
        },
    )


@router.post("/policies")
async def create_policy_form(
    request: Request,
    name: str = Form(...),
    kind: str = Form(...),
    definition: str = Form(...),
    db=Depends(get_db),
):
    """Create a new policy from the form."""
    try:
        definition_obj = json.loads(definition or "{}")
    except json.JSONDecodeError as e:
        cursor = db[POLICIES_COLLECTION].find({}).sort("_id", 1)
        docs = await cursor.to_list(length=None)
        policies: list[dict] = []
        for doc in docs:
            policies.append(
                {
                    "id": str(doc.get("_id")),
                    "name": doc.get("name", ""),
                    "kind": doc.get("kind", ""),
                    "version": doc.get("version", 1),
                    "created_at": doc.get("created_at"),
                }
            )
        return templates.TemplateResponse(
            "policies.html",
            {
                "request": request,
                "policies": policies,
                "error": f"Invalid JSON in definition: {e}",
                "name": name,
                "kind": kind,
                "definition": definition,
            },
        )

    now = datetime.now(timezone.utc)
    doc = {
        "name": name,
        "kind": kind,
        "definition": definition_obj,
        "version": 1,
        "created_at": now,
    }
    await db[POLICIES_COLLECTION].insert_one(doc)

    return RedirectResponse(url="/ui/policies", status_code=303)


@router.get("/approvals")
async def approvals_page(
    request: Request,
    status: str | None = None,
    db=Depends(get_db),
):
    """List approvals with optional status filter."""
    query = {} if not status or status == "all" else {"status": status}
    cursor = db[APPROVALS_COLLECTION].find(query).sort("created_at", -1)
    docs = await cursor.to_list(length=None)
    approvals: list[dict] = []
    for doc in docs:
        approvals.append(
            {
                "id": str(doc.get("_id")),
                "action_id": doc.get("action_id", ""),
                "agent_id": doc.get("agent_id", ""),
                "action_type": doc.get("action_type", ""),
                "resource": doc.get("resource", ""),
                "status": doc.get("status", ""),
                "risk_score": doc.get("risk_score", 0.0),
                "reason": doc.get("reason", ""),
                "created_at": doc.get("created_at"),
                "resolved_at": doc.get("resolved_at"),
                "resolved_by": doc.get("resolved_by"),
            }
        )

    return templates.TemplateResponse(
        "approvals.html",
        {
            "request": request,
            "approvals": approvals,
            "status": status or "pending",
        },
    )


def _parse_oid_for_ui(approval_id: str) -> ObjectId:
    try:
        return ObjectId(approval_id)
    except InvalidId:
        # For the UI we just redirect back; no 404 page needed.
        raise RedirectResponse(url="/ui/approvals", status_code=303)


@router.post("/approvals/{approval_id}/approve")
async def approve_approval(
    approval_id: str,
    db=Depends(get_db),
):
    """Mark an approval as approved."""
    try:
        oid = ObjectId(approval_id)
    except InvalidId:
        return RedirectResponse(url="/ui/approvals", status_code=303)

    now = datetime.now(timezone.utc)
    await db[APPROVALS_COLLECTION].find_one_and_update(
        {"_id": oid, "status": "pending"},
        {
            "$set": {
                "status": "approved",
                "resolved_at": now,
                "resolved_by": "ui",
            }
        },
        return_document=ReturnDocument.AFTER,
    )
    return RedirectResponse(url="/ui/approvals", status_code=303)


@router.post("/approvals/{approval_id}/deny")
async def deny_approval(
    approval_id: str,
    db=Depends(get_db),
):
    """Mark an approval as denied."""
    try:
        oid = ObjectId(approval_id)
    except InvalidId:
        return RedirectResponse(url="/ui/approvals", status_code=303)

    now = datetime.now(timezone.utc)
    await db[APPROVALS_COLLECTION].find_one_and_update(
        {"_id": oid, "status": "pending"},
        {
            "$set": {
                "status": "denied",
                "resolved_at": now,
                "resolved_by": "ui",
            }
        },
        return_document=ReturnDocument.AFTER,
    )
    return RedirectResponse(url="/ui/approvals", status_code=303)


