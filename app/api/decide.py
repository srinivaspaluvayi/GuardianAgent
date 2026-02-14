"""Optional synchronous-style decide: submit intent, get back intent_event_id to watch action.decision. Requires Redis."""
from datetime import datetime, timezone
from uuid import uuid4

import redis
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import get_settings
from app.streams.redis_streams import RedisStreams

router = APIRouter(tags=["decide"])


class ActionIntentSubmit(BaseModel):
    trace_id: str = Field(..., description="Trace id from agent")
    agent_id: str = ""
    session_id: str = ""
    user_id: str = ""
    action: dict = Field(..., description="type, tool, target, method?, args")
    context: dict = Field(default_factory=dict, description="user_prompt, data_classification, etc.")


class DecideAccepted(BaseModel):
    event_id: str
    trace_id: str
    message: str = "Intent submitted. Consume stream action.decision and match intent_event_id to get decision."


@router.post("/decide", response_model=DecideAccepted, status_code=202)
def submit_intent(body: ActionIntentSubmit):
    """Submit an action intent. Guardian worker will evaluate and emit to action.decision. Requires Redis. For testing without Redis, use POST /v1/evaluate instead."""
    event_id = str(uuid4())
    intent = {
        "event_id": event_id,
        "trace_id": body.trace_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent_id": body.agent_id,
        "session_id": body.session_id,
        "user_id": body.user_id,
        "action": body.action,
        "context": body.context,
    }
    settings = get_settings()
    try:
        bus = RedisStreams(settings.redis_url)
        bus.xadd(settings.stream_action_intent, intent)
    except redis.exceptions.ConnectionError as e:
        raise HTTPException(
            status_code=503,
            detail="Redis is not available. Start Redis (e.g. redis-server) to use /decide, or use POST /v1/evaluate for sync evaluation without Redis.",
        ) from e
    return DecideAccepted(
        event_id=event_id,
        trace_id=body.trace_id,
    )
