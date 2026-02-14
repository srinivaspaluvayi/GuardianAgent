"""Safe rewrite stub. Phase 2: use LLM to suggest minimal safe action."""
from typing import Any, Dict, Optional


def suggest_rewrite(intent: Dict[str, Any], reasons: list) -> Optional[Dict[str, Any]]:
    """
    Suggest a safer version of the action (e.g. redact PII, change destination).
    Stub: returns None; implement with LLM in Phase 2.
    """
    return None
