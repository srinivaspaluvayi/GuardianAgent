"""Evaluate action: policy engine + LLM (if unknown) + approval/rewrite."""
from fastapi import APIRouter, Depends

from app.db import get_db
from app.models import Action, EvaluateResponse
from app.pipeline import run_pipeline

router = APIRouter(tags=["decide"])


@router.post("/evaluate", response_model=EvaluateResponse)
async def evaluate_action_endpoint(
    action: Action,
    db=Depends(get_db),
):
    """Full pipeline: policy -> LLM if unknown -> decision. Uses shared run_pipeline."""
    return await run_pipeline(db, action)
