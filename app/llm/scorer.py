"""Calls LLM with action + context; returns risk score and decision (allow/block/needs_approval/rewrite)."""
import json
from typing import Any

from openai import AsyncOpenAI

from app.config import settings
from app.models import Action

# Decision: allow | block | needs_approval | rewrite
SCORER_SYSTEM = """You are a risk scorer for agent actions. Given an action (type, resource, payload summary), output JSON only with:
- "score": number in [0, 1] (0=no risk, 1=high risk)
- "decision": one of "allow", "block", "needs_approval", "rewrite"
- "reason": short explanation

Rules: Block or needs_approval for sensitive paths (/etc/, .env, keys), external sends, PII. Allow only clearly safe actions. Use rewrite when the action can be made safe by redacting or restricting."""


async def score_action(action: Action) -> tuple[float, str, str]:
    """
    Returns (score, decision, reason). decision is one of allow, block, needs_approval, rewrite.
    """
    if not settings.openai_api_key:
        # No key: treat as low risk allow for testing
        return 0.0, "allow", "no LLM configured"

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    payload_summary = json.dumps(action.payload)[:500] if action.payload else "{}"
    user_content = (
        f"Action type: {action.type}\nResource: {action.resource or '(none)'}\n"
        f"Payload (summary): {payload_summary}\n"
        "Output JSON with score, decision, reason only."
    )
    try:
        resp = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": SCORER_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            max_tokens=300,
        )
        text = resp.choices[0].message.content or "{}"
        # Parse JSON from response (may be wrapped in markdown)
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(l for l in lines if l.strip() != "```" and not l.strip().startswith("```json"))
        data = json.loads(text)
        score = float(data.get("score", 0.0))
        decision = str(data.get("decision", "allow")).lower()
        if decision not in ("allow", "block", "needs_approval", "rewrite"):
            decision = "allow"
        reason = str(data.get("reason", ""))[:500]
        return score, decision, reason
    except Exception as e:
        # On error, default to needs_approval so we don't allow blindly
        return 0.8, "needs_approval", f"scorer error: {e!s}"[:200]
