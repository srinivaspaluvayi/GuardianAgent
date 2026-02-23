"""Evaluates an action against JSON/DSL rules. Returns allowed/denied/unknown. No LLM, no I/O."""
import fnmatch
import re
from typing import Any

from app.models import Action

PolicyDecision = str  # "allowed" | "denied" | "unknown"

# Rule shape: {"effect": "allow"|"deny", "match": {"action_type": "...", "resource_pattern": "...", ...}}
# resource_pattern: glob (e.g. /etc/*) or regex (prefix with re:)


def _matches_pattern(pattern: str, value: str) -> bool:
    if pattern.startswith("re:"):
        try:
            return bool(re.search(pattern[3:], value))
        except re.error:
            return False
    return fnmatch.fnmatch(value, pattern)


def evaluate(action: Action, rules: list[dict[str, Any]]) -> PolicyDecision:
    """
    First matching rule wins. Default deny (unknown) if no rule matches.
    rules: list of {"effect": "allow"|"deny", "match": {"action_type": "...", "resource_pattern": "..."}}
    """
    for rule in rules:
        effect = rule.get("effect")
        match_spec = rule.get("match") or {}
        if effect not in ("allow", "deny"):
            continue
        # match action_type
        if "action_type" in match_spec:
            if not _matches_pattern(match_spec["action_type"], action.type):
                continue
        # match resource
        if "resource_pattern" in match_spec:
            if not _matches_pattern(match_spec["resource_pattern"], action.resource or ""):
                continue
        # optional payload_conditions: simple key presence or value match
        if "payload_conditions" in match_spec:
            conds = match_spec["payload_conditions"]
            if isinstance(conds, dict):
                for key, expected in conds.items():
                    if action.payload.get(key) != expected:
                        break
                else:
                    return "allowed" if effect == "allow" else "denied"
            continue
        return "allowed" if effect == "allow" else "denied"
    return "unknown"
