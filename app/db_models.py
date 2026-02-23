"""MongoDB collection names and helpers. No ORM; documents are dicts."""
from app.db import APPROVALS_COLLECTION, POLICIES_COLLECTION

__all__ = ["POLICIES_COLLECTION", "APPROVALS_COLLECTION"]
