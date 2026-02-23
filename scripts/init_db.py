"""Create MongoDB indexes. Run once; requires MONGODB_URL."""
import asyncio
from app.db import close_db, init_db, start_db

async def main():
    await start_db()
    try:
        await init_db()
        print("Indexes created.")
    finally:
        await close_db()

if __name__ == "__main__":
    asyncio.run(main())
