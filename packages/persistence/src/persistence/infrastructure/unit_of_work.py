"""Unit of Work pattern implementation with SQLAlchemy."""

from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from .repositories import (
    SqlCheckpointRepository,
    SqlDecisionRepository,
    SqlEvidenceRepository,
    SqlExecutionSessionRepository,
    SqlParkingItemRepository,
    SqlSpecificationRepository,
    SqlTaskRepository,
)


class SqlAlchemyUnitOfWork:
    """SQLAlchemy-based Unit of Work for coordinating repository operations."""

    def __init__(self, session_factory: sessionmaker[Session]):
        self._session_factory = session_factory
        self._session: Session | None = None

    def __enter__(self) -> "SqlAlchemyUnitOfWork":
        """Start a new database session."""
        self._session = self._session_factory()
        self.sessions = SqlExecutionSessionRepository(self._session)
        self.specifications = SqlSpecificationRepository(self._session)
        self.tasks = SqlTaskRepository(self._session)
        self.evidence = SqlEvidenceRepository(self._session)
        self.checkpoints = SqlCheckpointRepository(self._session)
        self.decisions = SqlDecisionRepository(self._session)
        self.parking_items = SqlParkingItemRepository(self._session)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Commit or rollback and close session."""
        if self._session:
            try:
                if exc_type is None:
                    self.commit()
                else:
                    self.rollback()
            except Exception:
                self.rollback()
                raise
            finally:
                self._session.close()
                self._session = None

    def commit(self) -> None:
        """Commit the current transaction."""
        if self._session:
            self._session.commit()

    def rollback(self) -> None:
        """Rollback the current transaction."""
        if self._session:
            self._session.rollback()
