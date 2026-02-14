"""Seed default policies into Postgres. Run after DB is up and tables created."""
import sys
from pathlib import Path

# Ensure app is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import get_db, init_db
from app.db_models import Policy
from app.policy.allowlists import EXTERNAL_DOMAINS_ALLOWLIST

POLICIES = [
    {
        "policy_id": "pii_external_exfiltration",
        "version": 1,
        "enabled": True,
        "priority": 100,
        "match": {
            "action.type": ["http.request", "email.send", "slack.post"],
            "context.data_classification": ["PII", "PHI", "PCI", "PII_POSSIBLE", "SECRET"],
        },
        "conditions": [
            {
                "not_in_allowlist": {
                    "action.target_domain": "EXTERNAL_DOMAINS_ALLOWLIST",
                }
            }
        ],
        "effect": "REQUIRE_APPROVAL",
        "risk_boost": 0.25,
        "message": "Sensitive data + external destination requires approval.",
    },
    {
        "policy_id": "block_secrets_anywhere",
        "version": 1,
        "enabled": True,
        "priority": 200,
        "match": {"context.data_classification": ["SECRET"]},
        "effect": "BLOCK",
        "risk_boost": 0.95,
        "message": "Secrets must never be transmitted.",
    },
]


def main():
    init_db()
    with get_db() as session:
        for p in POLICIES:
            policy_id = p["policy_id"]
            existing = session.query(Policy).filter(Policy.policy_id == policy_id).first()
            if existing:
                print(f"Skip (exists): {policy_id}")
                continue
            # Store as JSONB: conditions use string ref so store resolves on load
            policy_jsonb = {
                "policy_id": policy_id,
                "version": p["version"],
                "enabled": p["enabled"],
                "priority": p["priority"],
                "match": p["match"],
                "conditions": p.get("conditions", []),
                "effect": p["effect"],
                "risk_boost": p["risk_boost"],
                "message": p.get("message", ""),
            }
            row = Policy(
                policy_id=policy_id,
                version=p["version"],
                priority=p["priority"],
                policy_jsonb=policy_jsonb,
                enabled=p["enabled"],
            )
            session.add(row)
            print(f"Seeded: {policy_id}")
    print("Done.")


if __name__ == "__main__":
    main()
