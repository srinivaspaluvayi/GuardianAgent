"""SQLAlchemy session and Postgres setup."""
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import get_settings

Base = declarative_base()

_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        url = get_settings().database_url
        opts = dict(pool_pre_ping=True, echo=get_settings().debug)
        if url.startswith("sqlite"):
            opts["connect_args"] = {"check_same_thread": False}
        _engine = create_engine(url, **opts)
    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine(),
        )
    return _SessionLocal


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Yield a DB session; commits on success, rolls back on error."""
    SessionLocal = get_session_factory()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Create all tables. Use Alembic in production for migrations."""
    import app.db_models  # noqa: F401 - register tables with Base
    Base.metadata.create_all(bind=get_engine())
