"""LLM-based risk scoring. Supports Ollama (local, secure) or any OpenAI-compatible API."""
import json
import re
from typing import Any, Dict, List, Optional, Tuple

from app.config import get_settings


# Prompt tuned for a security-policy-trained model; adjust if your Ollama model expects different format
SYSTEM_PROMPT = """You are a security policy evaluator. Given an action an agent is about to perform, output a risk score from 0.0 (no risk) to 1.0 (maximum risk) and brief reasons.

Apply your security policy training. Consider: data sensitivity (PII, PHI, PCI, secrets), destination (internal vs external), exfiltration risk, and whether the action matches safe practices.

Respond with ONLY a single JSON object, no other text, in this exact format:
{"risk_score": <number 0.0-1.0>, "risk_factors": ["reason1", "reason2", ...]}"""


def _build_user_message(intent: Dict[str, Any]) -> str:
    action = intent.get("action", {}) or {}
    context = intent.get("context", {}) or {}
    # Redact long payloads for token safety; keep structure
    args_preview = str(action.get("args", {}))[:500]
    return (
        f"Action type: {action.get('type', '')}\n"
        f"Tool: {action.get('tool', '')}\n"
        f"Target: {action.get('target', '')}\n"
        f"Target domain: {action.get('target_domain', '')}\n"
        f"Args (preview): {args_preview}\n"
        f"Data classification: {context.get('data_classification', [])}\n"
        f"Workspace: {context.get('workspace', '')}"
    )


def _parse_llm_response(text: str) -> Tuple[float, List[str]]:
    """Extract risk_score and risk_factors from LLM response. Returns (0.0, []) on parse failure."""
    text = text.strip()
    # Try to find a JSON object in the response
    match = re.search(r"\{[^{}]*\"risk_score\"[^{}]*\}", text)
    if not match:
        match = re.search(r"\{[\s\S]*?\}", text)
    if not match:
        return 0.0, []
    try:
        data = json.loads(match.group())
        score = float(data.get("risk_score", 0.0))
        score = max(0.0, min(1.0, score))
        factors = data.get("risk_factors") or []
        if isinstance(factors, list):
            factors = [str(f) for f in factors[:10]]
        else:
            factors = []
        return score, factors
    except (json.JSONDecodeError, TypeError, ValueError):
        return 0.0, []


def _llm_enabled(settings) -> bool:
    """Use LLM when Ollama base_url is set or when API key is set (OpenAI etc.)."""
    if settings.llm_base_url and settings.llm_base_url.strip():
        return True
    if settings.llm_api_key and settings.llm_api_key.strip():
        return True
    return False


def score_risk(intent: Dict[str, Any]) -> Tuple[float, List[str], Optional[Dict[str, Any]]]:
    """
    Returns (risk_score 0.0-1.0, risk_factors/reasons, optional safe_rewrite).
    Uses Ollama if GUARDIAN_LLM_BASE_URL is set (e.g. http://localhost:11434/v1), or OpenAI if GUARDIAN_LLM_API_KEY is set.
    Otherwise returns (0.0, [], None) for policy-only scoring.
    """
    settings = get_settings()
    if not _llm_enabled(settings):
        return 0.0, [], None

    try:
        from openai import OpenAI

        # Ollama does not require an API key; OpenAI client needs a non-empty string when base_url is set
        api_key = (settings.llm_api_key or "").strip() or "ollama"
        base_url = (settings.llm_base_url or "").strip() or None

        client = OpenAI(api_key=api_key, base_url=base_url)
        resp = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_message(intent)},
            ],
            max_tokens=256,
            temperature=0.1,
        )
        content = (resp.choices[0].message.content or "").strip()
        score, reasons = _parse_llm_response(content)
        return score, reasons, None
    except Exception:
        # On any LLM failure, fall back to no LLM signal (policy-only)
        return 0.0, [], None
