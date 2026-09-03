"""Database configuration and session management."""

from sqlalchemy import Engine, event
from sqlalchemy import create_engine as sa_create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base


def create_engine(database_url: str = "sqlite:///.coh/coh.db") -> Engine:
    """Create SQLAlchemy engine with SQLite WAL mode."""
    engine = sa_create_engine(
        database_url,
        echo=False,
        connect_args={"check_same_thread": False}
        if database_url.startswith("sqlite")
        else {},
    )
    return engine


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record) -> None:  # type: ignore
    """Enable WAL mode and other SQLite pragmas for better concurrency."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def get_session_factory(engine: Engine) -> sessionmaker:
    """Create a sessionmaker bound to the engine."""
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db(engine: Engine) -> None:
    """Initialize database schema (for testing only, use Alembic in production)."""
    Base.metadata.create_all(bind=engine)
