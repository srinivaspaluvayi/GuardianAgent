"""FastAPI app. Lifespan: MongoDB only (Redis/stream consumer omitted until deployment)."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse, RedirectResponse, Response

from app.api.approvals import router as approvals_router
from app.api.decide import router as decide_router
from app.api.policies import router as policies_router
from app.ui.router import router as ui_router
from app.config import settings
from app.db import check_db, close_db, init_db, start_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_db()
    try:
        await init_db()
    except Exception:
        # MongoDB may be down (e.g. local dev); app still starts, /health reports 503
        pass
    try:
        yield
    finally:
        await close_db()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(policies_router)
app.include_router(decide_router)
app.include_router(approvals_router)
app.include_router(ui_router)


@app.get("/", include_in_schema=False)
async def root():
    """Redirect bare root to UI evaluate form."""
    return RedirectResponse(url="/ui/evaluate")


@app.get(
    "/favicon.ico",
    include_in_schema=False,
)
async def favicon() -> Response:
    """Return empty 204 so browsers stop 404-ing favicon."""
    return Response(status_code=204)


@app.get(
    "/apple-touch-icon.png",
    include_in_schema=False,
)
@app.get(
    "/apple-touch-icon-precomposed.png",
    include_in_schema=False,
)
async def apple_touch_icon() -> Response:
    """Return empty 204 so browsers stop 404-ing Apple touch icons."""
    return Response(status_code=204)


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