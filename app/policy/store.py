"""Load policies from Postgres (with optional in-memory cache)."""
from typing import Any, Dict, List

from app.db import get_db
from app.db_models import Policy as PolicyModel
from app.policy.allowlists import EXTERNAL_DOMAINS_ALLOWLIST


def _policy_row_to_dict(row: PolicyModel) -> Dict[str, Any]:
    p = dict(row.policy_jsonb)
    p["policy_id"] = row.policy_id
    p["version"] = row.version
    p["priority"] = row.priority
    p["enabled"] = row.enabled
    return p


def _resolve_allowlist_ref(policy: Dict[str, Any]) -> Dict[str, Any]:
    """Replace allowlist name (string) with actual list for engine."""
    out = dict(policy)
    conditions = list(out.get("conditions", []))
    resolved = []
    for cond in conditions:
        c = dict(cond)
        if "not_in_allowlist" in c:
            spec = dict(c["not_in_allowlist"])
            for k, v in list(spec.items()):
                if v == "EXTERNAL_DOMAINS_ALLOWLIST":
                    spec[k] = list(EXTERNAL_DOMAINS_ALLOWLIST)
            c["not_in_allowlist"] = spec
        if "in_allowlist" in c:
            spec = dict(c["in_allowlist"])
            for k, v in list(spec.items()):
                if v == "EXTERNAL_DOMAINS_ALLOWLIST":
                    spec[k] = list(EXTERNAL_DOMAINS_ALLOWLIST)
            c["in_allowlist"] = spec
        resolved.append(c)
    out["conditions"] = resolved
    return out


def load_policies_from_db() -> List[Dict[str, Any]]:
    """Load all enabled policies from Postgres (no cache)."""
    with get_db() as session:
        rows = session.query(PolicyModel).filter(PolicyModel.enabled.is_(True)).all()
        return [_resolve_allowlist_ref(_policy_row_to_dict(r)) for r in rows]


def get_policies_cached(cache: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Return policies; cache key can be invalidated on policy update. For worker, refresh each loop or every N seconds."""
    return load_policies_from_db()
