"""Pytest fixtures for persistence tests."""

import tempfile

import pytest
from persistence.infrastructure.database import init_db
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def temp_db() -> str:
    """Create a temporary database file."""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_file.close()
    return f"sqlite:///{temp_file.name}"


@pytest.fixture
def engine(temp_db: str) -> Engine:
    """Create a SQLAlchemy engine for testing."""
    engine = create_engine(temp_db, connect_args={"check_same_thread": False})
    init_db(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session_factory(engine: Engine) -> sessionmaker:
    """Create a sessionmaker for testing."""
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)
