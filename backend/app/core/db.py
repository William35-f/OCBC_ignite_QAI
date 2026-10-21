"""SQLAlchemy engine and session helpers (SQLite)."""
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


settings.storage_dir.mkdir(parents=True, exist_ok=True)
engine = create_engine(settings.db_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db() -> None:
    """Create all tables (simple prototype: no migrations)."""
    import app.models  # noqa: F401  (registers the tables)

    Base.metadata.create_all(engine)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
