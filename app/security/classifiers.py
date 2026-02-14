"""Lightweight PII/secret detection (regex-based MVP)."""
import re
from typing import Any, Dict, List

RE_API_KEY = re.compile(
    r"(api[_-]?key|secret|token)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}['\"]?",
    re.I,
)
RE_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
RE_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")


def _flatten_args(intent: Dict[str, Any]) -> str:
    action = intent.get("action", {}) or {}
    args = action.get("args", {}) or {}
    return str(args)


def classify_payload(intent: Dict[str, Any]) -> List[str]:
    text = _flatten_args(intent)
    tags: List[str] = []

    if RE_API_KEY.search(text):
        tags.append("SECRET")
    if RE_SSN.search(text):
        tags.append("PII")
    if RE_EMAIL.search(text):
        tags.append("PII")

    return tags
