"""Unit tests for policy engine."""
import pytest
from app.policy.engine import decide, policy_matches, severity_from_score, _target_domain

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


def test_severity_from_score():
    assert severity_from_score(0.2) == "LOW"
    assert severity_from_score(0.5) == "MEDIUM"
    assert severity_from_score(0.75) == "HIGH"
    assert severity_from_score(0.95) == "CRITICAL"


def test_target_domain():
    assert _target_domain("https://api.slack.com/chat.postMessage") == "api.slack.com"
    assert _target_domain("https://api.company.com/report") == "api.company.com"
    assert _target_domain("") == ""


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
