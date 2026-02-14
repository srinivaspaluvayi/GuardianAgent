"""Synchronous evaluate: run Guardian in-process and return decision (no Redis). For API/Postman testing."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.llm.scorer import score_risk as llm_score_risk
from app.policy.engine import decide, _target_domain
from app.policy.store import load_policies_from_db
from app.security.classifiers import classify_payload

router = APIRouter(tags=["evaluate"])


class EvaluateRequest(BaseModel):
    """Same shape as action intent (trace_id, action, context)."""
    trace_id: str = Field(..., description="Trace id from agent")
    agent_id: str = ""
    session_id: str = ""
    user_id: str = ""
    action: dict = Field(..., description="type, tool, target, method?, args")
    context: dict = Field(default_factory=dict, description="user_prompt, data_classification, etc.")


class RiskOut(BaseModel):
    score: float
    severity: str
    reasons: list[str]


class EvaluateResponse(BaseModel):
    decision: str  # ALLOW | REWRITE | BLOCK | REQUIRE_APPROVAL
    risk: RiskOut
    policy_hits: list[str] = []
    rewrite: dict | None = None
    approval_required: bool = False


@router.post("/evaluate", response_model=EvaluateResponse)
def evaluate_intent(body: EvaluateRequest):
    """
    Run Guardian in-process: classifiers + policy engine.
    Returns the decision in the response (no Redis, no worker).
    Use this for Postman/API testing. Policies are loaded from Postgres.
    """
    intent = {
        "trace_id": body.trace_id,
        "agent_id": body.agent_id,
        "session_id": body.session_id,
        "user_id": body.user_id,
        "action": dict(body.action),
        "context": dict(body.context),
    }
    intent.setdefault("action", {})
    intent["action"]["target_domain"] = _target_domain(intent["action"].get("target", ""))

    tags = classify_payload(intent)
    ctx = intent.setdefault("context", {})
    ctx.setdefault("data_classification", [])
    for t in tags:
        if t not in ctx["data_classification"]:
            ctx["data_classification"].append(t)

    try:
        policies = load_policies_from_db()
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Could not load policies from database. Run init_db and seed_policies. Error: {e!s}",
        ) from e

    if not policies:
        raise HTTPException(
            status_code=503,
            detail="No policies in database. Run: python scripts/seed_policies.py",
        )

    llm_score, llm_reasons, llm_rewrite = llm_score_risk(intent)
    decision, payload = decide(
        intent, policies,
        llm_score=llm_score if llm_score is not None else None,
        llm_reasons=llm_reasons or None,
        llm_rewrite=llm_rewrite,
    )

    return EvaluateResponse(
        decision=decision,
        risk=RiskOut(
            score=payload["risk"]["score"],
            severity=payload["risk"]["severity"],
            reasons=payload["risk"].get("reasons") or [],
        ),
        policy_hits=payload.get("policy_hits") or [],
        rewrite=payload.get("rewrite"),
        approval_required=(decision == "REQUIRE_APPROVAL"),
    )
