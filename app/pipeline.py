"""Single pipeline: policy -> LLM (if unknown) -> decision. Used by API (and stream consumer later)."""
from datetime import datetime, timezone

from app.db import APPROVALS_COLLECTION
from app.llm.rewrite import rewrite_action
from app.llm.scorer import score_action
from app.models import Action, EvaluateResponse
from app.policy.store import evaluate_action


async def run_pipeline(db, action: Action) -> EvaluateResponse:
    """
    Full pipeline: policy engine -> if unknown then LLM scorer -> return decision.
    For needs_approval we persist to approval_requests and return approval_id.
    """
    policy_decision = await evaluate_action(db, action)

    if policy_decision == "allowed":
        return EvaluateResponse(
            action_id=action.action_id,
            policy_decision=policy_decision,
            decision="allowed",
            reason="policy allow",
        )
    if policy_decision == "denied":
        return EvaluateResponse(
            action_id=action.action_id,
            policy_decision=policy_decision,
            decision="blocked",
            reason="policy deny",
        )

    score, llm_decision, reason = await score_action(action)

    if llm_decision == "allow":
        return EvaluateResponse(
            action_id=action.action_id,
            policy_decision=policy_decision,
            decision="allowed",
            reason=reason,
            score=score,
        )
    if llm_decision == "block":
        return EvaluateResponse(
            action_id=action.action_id,
            policy_decision=policy_decision,
            decision="blocked",
            reason=reason,
            score=score,
        )
    if llm_decision == "needs_approval":
        now = datetime.now(timezone.utc)
        doc = {
            "action_id": action.action_id,
            "agent_id": action.agent_id,
            "action_type": action.type,
            "resource": action.resource or "",
            "payload": action.payload,
            "risk_score": score,
            "reason": reason,
            "status": "pending",
            "created_at": now,
        }
        result = await db[APPROVALS_COLLECTION].insert_one(doc)
        return EvaluateResponse(
            action_id=action.action_id,
            policy_decision=policy_decision,
            decision="needs_approval",
            reason=reason,
            score=score,
            approval_id=str(result.inserted_id),
        )
    rewritten = await rewrite_action(action)
    return EvaluateResponse(
        action_id=action.action_id,
        policy_decision=policy_decision,
        decision="rewritten",
        reason=reason,
        score=score,
        rewritten_payload=rewritten,
    )
