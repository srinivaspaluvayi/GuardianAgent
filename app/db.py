"""MongoDB connection and database. Async via Motor."""
from collections.abc import AsyncGenerator

from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings

# Collection names
POLICIES_COLLECTION = "policies"
APPROVALS_COLLECTION = "approval_requests"

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    """Return the global Motor client. Call after start_db()."""
    if _client is None:
        raise RuntimeError("DB not started; call start_db() in lifespan first.")
    return _client


async def start_db() -> None:
    """Create MongoDB client. Call once at app startup."""
    global _client
    _client = AsyncIOMotorClient(settings.mongodb_url)


async def close_db() -> None:
    """Close MongoDB client. Call at app shutdown."""
    global _client
    if _client is not None:
        _client.close()
        _client = None


def get_database():
    """Return the Guardian database (sync access for dependency injection)."""
    return get_client()[settings.mongodb_db_name]


async def init_db() -> None:
    """Create indexes. Safe to call every startup."""
    db = get_database()
    await db[POLICIES_COLLECTION].create_index("name")
    await db[APPROVALS_COLLECTION].create_index("status")
    await db[APPROVALS_COLLECTION].create_index("created_at")


async def check_db() -> bool:
    """Returns True if MongoDB is reachable."""
    try:
        await get_client().admin.command("ping")
        return True
    except Exception:
        return False


async def get_db() -> AsyncGenerator:
    """FastAPI dependency: yield the database instance."""
    yield get_database()
