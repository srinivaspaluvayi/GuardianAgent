"""DeepEval compliance tests: risky intents blocked/approval required, benign allowed."""
import pytest
from app.policy.engine import decide

POLICIES = [
    {
        "policy_id": "block_secrets_anywhere",
        "priority": 200,
        "enabled": True,
        "match": {"context.data_classification": ["SECRET"]},
        "effect": "BLOCK",
        "risk_boost": 0.95,
        "message": "Secrets must never be transmitted.",
    },
    {
        "policy_id": "pii_external_exfiltration",
        "priority": 100,
        "enabled": True,
        "match": {
            "action.type": ["http.request"],
            "context.data_classification": ["PII"],
        },
        "conditions": [
            {"not_in_allowlist": {"action.target_domain": ["api.company.com"]}}
        ],
        "effect": "REQUIRE_APPROVAL",
        "risk_boost": 0.25,
        "message": "Sensitive data + external destination requires approval.",
    },
]


def test_blocks_secrets():
    intent = {
        "action": {
            "type": "http.request",
            "target": "https://example.com",
            "target_domain": "example.com",
            "args": {"text": "api_key=ABCDEF1234567890ZZZZ"},
        },
        "context": {"data_classification": ["SECRET"]},
    }
    decision, payload = decide(intent, POLICIES)
    assert decision == "BLOCK"
    assert payload["risk"]["severity"] in ["HIGH", "CRITICAL"]


def test_requires_approval_for_pii_external():
    intent = {
        "action": {
            "type": "http.request",
            "target": "https://slack.com/api/chat.postMessage",
            "target_domain": "slack.com",
            "args": {"text": "email: a@b.com"},
        },
        "context": {"data_classification": ["PII"]},
    }
    decision, _ = decide(intent, POLICIES)
    assert decision == "REQUIRE_APPROVAL"


def test_allows_internal_domain():
    intent = {
        "action": {
            "type": "http.request",
            "target": "https://api.company.com/report",
            "target_domain": "api.company.com",
            "args": {"text": "email: a@b.com"},
        },
        "context": {"data_classification": ["PII"]},
    }
    decision, _ = decide(intent, POLICIES)
    assert decision == "ALLOW"
