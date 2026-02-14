"""Guardian Supervisor FastAPI application."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.api.approvals import router as approvals_router
from app.api.decide import router as decide_router
from app.api.evaluate import router as evaluate_router
from app.api.health import router as health_router
from app.api.policies import router as policies_router
from app.config import get_settings
from app.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title=get_settings().app_name,
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/", include_in_schema=False)
def root():
    """Redirect to API docs."""
    return RedirectResponse(url="/docs", status_code=302)


app.include_router(health_router, prefix="/v1")
app.include_router(evaluate_router, prefix="/v1")
app.include_router(decide_router, prefix="/v1")
app.include_router(approvals_router, prefix="/v1")
app.include_router(policies_router, prefix="/v1")
