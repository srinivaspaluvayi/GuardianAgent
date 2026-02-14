"""Guardian consumer: read action.intent, evaluate, emit action.decision, persist to Postgres."""
import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.config import get_settings
from app.db import get_db, init_db
from app.db_models import Action, Approval, Decision
from app.llm.scorer import score_risk as llm_score_risk
from app.policy.engine import decide, _target_domain
from app.policy.store import load_policies_from_db
from app.security.classifiers import classify_payload
from app.streams.redis_streams import RedisStreams


def _args_hash(args: Dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(args, sort_keys=True).encode()).hexdigest()


def run_guardian() -> None:
    settings = get_settings()
    init_db()
    bus = RedisStreams(settings.redis_url)
    stream_intent = settings.stream_action_intent
    stream_decision = settings.stream_action_decision
    group = settings.consumer_group
    consumer = settings.consumer_name

    bus.ensure_group(stream_intent, group)

    while True:
        resp = bus.xreadgroup(
            stream_intent, group, consumer, count=10, block_ms=2000
        )
        if not resp:
            continue

        for _stream_key, msgs in resp:
            for msg_id, fields in msgs:
                raw = fields.get("json")
                if not raw:
                    bus.xack(stream_intent, group, msg_id)
                    continue
                intent = json.loads(raw)

                intent.setdefault("action", {})
                intent["action"]["target_domain"] = _target_domain(
                    intent["action"].get("target", "")
                )

                tags = classify_payload(intent)
                ctx = intent.setdefault("context", {})
                ctx.setdefault("data_classification", [])
                for t in tags:
                    if t not in ctx["data_classification"]:
                        ctx["data_classification"].append(t)

                policies = load_policies_from_db()
                llm_score, llm_reasons, llm_rewrite = llm_score_risk(intent)
                decision_result, payload = decide(
                    intent, policies,
                    llm_score=llm_score if llm_score is not None else None,
                    llm_reasons=llm_reasons or None,
                    llm_rewrite=llm_rewrite,
                )

                request_id = None
                with get_db() as session:
                    action = Action(
                        event_id=intent["event_id"],
                        trace_id=intent["trace_id"],
                        agent_id=intent.get("agent_id", ""),
                        action_type=intent["action"].get("type", ""),
                        target=intent["action"].get("target", ""),
                        args_hash=_args_hash(intent["action"].get("args", {})),
                        context_jsonb=intent.get("context"),
                    )
                    session.add(action)

                    decision_event_id = str(uuid.uuid4())
                    dec = Decision(
                        event_id=decision_event_id,
                        intent_event_id=intent["event_id"],
                        decision=decision_result,
                        risk_score=payload["risk"]["score"],
                        severity=payload["risk"]["severity"],
                        reasons_jsonb=payload["risk"].get("reasons"),
                        policy_hits_jsonb=payload.get("policy_hits"),
                        rewrite_jsonb=payload.get("rewrite"),
                    )
                    session.add(dec)
                    session.flush()

                    if decision_result == "REQUIRE_APPROVAL":
                        approval = Approval(
                            request_id=str(uuid.uuid4()),
                            intent_event_id=intent["event_id"],
                            decision_event_id=decision_event_id,
                            status="PENDING",
                        )
                        session.add(approval)
                        session.flush()
                        request_id = approval.request_id

                decision_event = {
                    "event_id": decision_event_id,
                    "trace_id": intent["trace_id"],
                    "intent_event_id": intent["event_id"],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "decision": decision_result,
                    "risk": payload["risk"],
                    "policy_hits": payload.get("policy_hits", []),
                    "rewrite": payload.get("rewrite"),
                    "approval": {
                        "required": decision_result == "REQUIRE_APPROVAL",
                        "request_id": request_id,
                    },
                }

                bus.xadd(stream_decision, decision_event)
                bus.xack(stream_intent, group, msg_id)


if __name__ == "__main__":
    run_guardian()
