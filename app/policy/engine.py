"""Policy evaluation and decision logic."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

Decision = str  # "ALLOW" | "BLOCK" | "REQUIRE_APPROVAL" | "REWRITE"


@dataclass
class PolicyHit:
    policy_id: str
    effect: Decision
    message: str
    risk_boost: float


def _get(d: Dict[str, Any], path: str) -> Any:
    cur: Any = d
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _has_any(haystack: List[str], needles: List[str]) -> bool:
    if not haystack:
        return False
    hs = set(x.upper() for x in haystack)
    return any(n.upper() in hs for n in needles)


def _target_domain(target: str) -> str:
    try:
        u = urlparse(target)
        return (u.netloc or "").lower()
    except Exception:
        return ""


def policy_matches(policy: Dict[str, Any], intent: Dict[str, Any]) -> bool:
    match = policy.get("match", {})
    for k, expected in match.items():
        actual = _get(intent, k)
        if isinstance(expected, list):
            if isinstance(actual, list):
                if not _has_any(actual, expected):
                    return False
            else:
                if actual not in expected:
                    return False
        else:
            if actual != expected:
                return False

    for cond in policy.get("conditions", []):
        if "not_in_allowlist" in cond:
            spec = cond["not_in_allowlist"]
            field, allowlist = next(iter(spec.items()))
            if isinstance(allowlist, set):
                allowlist = list(allowlist)
            value = _get(intent, field)
            if field == "action.target_domain":
                value = _target_domain(_get(intent, "action.target") or "")
            if value in allowlist:
                return False
        if "in_allowlist" in cond:
            spec = cond["in_allowlist"]
            field, allowlist = next(iter(spec.items()))
            if isinstance(allowlist, set):
                allowlist = list(allowlist)
            value = _get(intent, field)
            if field == "action.target_domain":
                value = _target_domain(_get(intent, "action.target") or "")
            if value not in allowlist:
                return False
    return True


def severity_from_score(score: float) -> str:
    if score >= 0.90:
        return "CRITICAL"
    if score >= 0.70:
        return "HIGH"
    if score >= 0.40:
        return "MEDIUM"
    return "LOW"


def decide(
    intent: Dict[str, Any],
    policies: List[Dict[str, Any]],
    llm_score: Optional[float] = None,
    llm_reasons: Optional[List[str]] = None,
    llm_rewrite: Optional[Dict[str, Any]] = None,
) -> Tuple[Decision, Dict[str, Any]]:
    """
    Deterministic baseline + optional LLM signal.
    Final decision is "most restrictive" among policy hits and score thresholds.
    """
    policies_sorted = sorted(policies, key=lambda p: int(p.get("priority", 0)), reverse=True)

    hits: List[PolicyHit] = []
    base_score = 0.0
    for p in policies_sorted:
        if not p.get("enabled", True):
            continue
        if policy_matches(p, intent):
            hits.append(
                PolicyHit(
                    policy_id=p["policy_id"],
                    effect=p["effect"],
                    message=p.get("message", ""),
                    risk_boost=float(p.get("risk_boost", 0.0)),
                )
            )
            base_score += float(p.get("risk_boost", 0.0))

    score = base_score
    reasons = [h.message for h in hits if h.message]

    if llm_score is not None:
        score = max(score, float(llm_score))
    if llm_reasons:
        reasons.extend(llm_reasons)

    rank = {"ALLOW": 0, "REWRITE": 1, "REQUIRE_APPROVAL": 2, "BLOCK": 3}
    decision: Decision = "ALLOW"

    for h in hits:
        if rank[h.effect] > rank[decision]:
            decision = h.effect

    if score > 0.85:
        decision = "BLOCK" if rank["BLOCK"] > rank[decision] else decision
    elif score > 0.60:
        decision = "REQUIRE_APPROVAL" if rank["REQUIRE_APPROVAL"] > rank[decision] else decision
    elif score > 0.30:
        if llm_rewrite is not None:
            decision = "REWRITE" if rank["REWRITE"] > rank[decision] else decision

    payload = {
        "risk": {
            "score": round(score, 4),
            "severity": severity_from_score(score),
            "reasons": reasons[:10],
        },
        "policy_hits": [h.policy_id for h in hits],
        "rewrite": llm_rewrite if decision == "REWRITE" else None,
    }
    return decision, payload
