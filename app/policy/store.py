"""Loads policy definitions from MongoDB and feeds them to the engine."""
from app.db import POLICIES_COLLECTION
from app.models import Action
from app.policy.engine import evaluate


def _rules_from_docs(docs: list[dict]) -> list[dict]:
    rules: list[dict] = []
    for doc in docs:
        defn = doc.get("definition") or {}
        if isinstance(defn, dict) and "rules" in defn:
            rules.extend(defn["rules"])
    return rules


async def get_rules(db) -> list[dict]:
    """Load all policy rules from MongoDB."""
    cursor = db[POLICIES_COLLECTION].find({})
    docs = await cursor.to_list(length=None)
    return _rules_from_docs(docs)


async def evaluate_action(db, action: Action) -> str:
    """Load rules from DB and evaluate action. Returns allowed | denied | unknown."""
    rules = await get_rules(db)
    return evaluate(action, rules)
