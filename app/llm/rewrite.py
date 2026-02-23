"""Calls LLM to produce a safe version of the action payload; returns rewritten payload for the allow path."""
import json
from typing import Any

from openai import AsyncOpenAI

from app.config import settings
from app.models import Action

REWRITE_SYSTEM = """You are a safety rewriter. Given an action with type, resource, and payload, output a JSON object that is a safe version of the payload: redact PII (replace with placeholders like [REDACTED]), remove or restrict sensitive fields, keep the structure valid. Return only the new JSON object, no explanation."""


async def rewrite_action(action: Action) -> dict[str, Any]:
    """Returns a rewritten (safe) payload. If LLM fails or is not configured, returns a minimal safe payload."""
    if not settings.openai_api_key:
        return _minimal_safe_payload(action.payload)

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    user_content = (
        f"Action type: {action.type}\nResource: {action.resource or '(none)'}\n"
        f"Payload to make safe: {json.dumps(action.payload)}"
    )
    try:
        resp = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": REWRITE_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            max_tokens=1000,
        )
        text = (resp.choices[0].message.content or "{}").strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(l for l in lines if l.strip() != "```" and not l.strip().startswith("```json"))
        return json.loads(text)
    except Exception:
        return _minimal_safe_payload(action.payload)


def _minimal_safe_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Strip known sensitive keys; return copy."""
    sensitive_keys = {"password", "secret", "token", "api_key", "ssn", "authorization"}
    out = {}
    for k, v in (payload or {}).items():
        if k.lower() in sensitive_keys:
            out[k] = "[REDACTED]"
        elif isinstance(v, dict):
            out[k] = _minimal_safe_payload(v)
        else:
            out[k] = v
    return out if out else {}
