"""FastAPI app. Lifespan: MongoDB only (Redis/stream consumer omitted until deployment)."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.approvals import router as approvals_router
from app.api.decide import router as decide_router
from app.api.policies import router as policies_router
from app.config import settings
from app.db import check_db, close_db, init_db, start_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_db()
    await init_db()
    try:
        yield
    finally:
        await close_db()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(policies_router)
app.include_router(decide_router)
app.include_router(approvals_router)


@app.get("/health")
async def health():
    """Returns 200 only if MongoDB is up. Redis check added at deployment."""
    db_ok = await check_db()
    if not db_ok:
        return JSONResponse(
            content={"status": "unhealthy", "db": "down"},
            status_code=503,
        )
    return {"status": "ok", "db": "up"}