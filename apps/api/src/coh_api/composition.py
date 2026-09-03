"""Service composition and dependency wiring."""

from pathlib import Path

from coh_application import ForegroundService, SpecGateService
from persistence.infrastructure.database import create_engine, get_session_factory
from persistence.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


class ServiceContainer:
    """Container for application services with shared UnitOfWork factory."""

    def __init__(self, database_url: str | None = None):
        """Initialize service container with database connection."""
        if database_url is None:
            # Default to .coh/coh.db in current working directory
            coh_dir = Path.cwd() / ".coh"
            coh_dir.mkdir(exist_ok=True)
            database_url = f"sqlite:///{coh_dir / 'coh.db'}"

        self.engine = create_engine(database_url)
        self.session_factory = get_session_factory(self.engine)

    def create_uow(self) -> SqlAlchemyUnitOfWork:
        """Create a new Unit of Work instance."""
        return SqlAlchemyUnitOfWork(self.session_factory)

    def spec_gate_service(self, uow: SqlAlchemyUnitOfWork) -> SpecGateService:
        """Create SpecGateService with provided UnitOfWork."""
        return SpecGateService(uow)

    def foreground_service(self, uow: SqlAlchemyUnitOfWork) -> ForegroundService:
        """Create ForegroundService with provided UnitOfWork."""
        return ForegroundService(uow)


# Global service container (initialized on app startup)
_container: ServiceContainer | None = None


def init_services(database_url: str | None = None) -> None:
    """Initialize global service container."""
    global _container
    # Skip if already initialized (e.g., by tests)
    if _container is not None:
        return
    _container = ServiceContainer(database_url)


def get_container() -> ServiceContainer:
    """Get global service container."""
    if _container is None:
        raise RuntimeError(
            "Service container not initialized. Call init_services first."
        )
    return _container
