"""
Abstract base classes and interfaces.

Defines contracts that implementations must follow,
enabling dependency inversion and loose coupling.
"""

from abc import ABC, abstractmethod
from typing import Any, Generic, Protocol, TypeVar, runtime_checkable

from rsw.state.schemas import DriverState, RaceState

# ============================================================================
# Type Variables
# ============================================================================

T = TypeVar("T")
TRequest = TypeVar("TRequest")
TResponse = TypeVar("TResponse")


# ============================================================================
# Data Provider Interface (Abstraction)
# ============================================================================


class IDataProvider(ABC):
    """
    Abstract interface for F1 data providers.

    Implementations could be:
    - OpenF1Client (live API)
    - CachedDataProvider (from JSON files)
    - MockDataProvider (for testing)

    Follows: Interface Segregation, Dependency Inversion
    """

    @abstractmethod
    async def get_sessions(self, year: int) -> list[Any]:
        """Get available sessions for a year."""
        pass

    @abstractmethod
    async def get_drivers(self, session_key: int) -> list[Any]:
        """Get drivers in a session."""
        pass

    @abstractmethod
    async def get_laps(self, session_key: int, driver_number: int | None = None) -> list[Any]:
        """Get lap data."""
        pass

    @abstractmethod
    async def get_stints(self, session_key: int) -> list[Any]:
        """Get stint data."""
        pass

    @abstractmethod
    async def get_pits(self, session_key: int) -> list[Any]:
        """Get pit stop data."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close connections."""
        pass


# ============================================================================
# State Store Interface
# ============================================================================


@runtime_checkable
class IStateStore(Protocol):
    """
    Protocol for race state storage.

    Using Protocol allows structural subtyping without inheritance.

    Follows: Interface Segregation
    """

    async def get_state(self) -> RaceState:
        """Get current state."""
        ...

    async def update_state(self, state: RaceState) -> None:
        """Update state."""
        ...

    def subscribe(self, callback: Any) -> str:
        """Subscribe to updates."""
        ...

    def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from updates."""
        ...


# ============================================================================
# Strategy Calculator Interface
# ============================================================================


class IStrategyCalculator(ABC):
    """
    Abstract interface for strategy calculations.

    Allows different strategy implementations:
    - SimpleStrategy (rule-based)
    - MLStrategy (machine learning)
    - HybridStrategy (combined approach)

    Follows: Open/Closed Principle
    """

    @abstractmethod
    def calculate_pit_window(
        self,
        driver: DriverState,
        total_laps: int,
        pit_loss: float,
    ) -> dict:
        """Calculate optimal pit window."""
        pass

    @abstractmethod
    def get_recommendation(
        self,
        driver: DriverState,
        race_state: RaceState,
    ) -> dict:
        """Get pit recommendation."""
        pass


# ============================================================================
# Model Interface
# ============================================================================


class IModel(ABC, Generic[TRequest, TResponse]):
    """
    Generic interface for ML models.

    Follows: Single Responsibility, Interface Segregation
    """

    @abstractmethod
    def fit(self, data: TRequest) -> None:
        """Train/update the model."""
        pass

    @abstractmethod
    def predict(self, data: TRequest) -> TResponse:
        """Make predictions."""
        pass

    @abstractmethod
    def get_confidence(self) -> float:
        """Get model confidence."""
        pass


# ============================================================================
# Repository Interface (Data Access)
# ============================================================================


class IRepository(ABC, Generic[T]):
    """
    Generic repository interface for data access.

    Separates data access from business logic.

    Follows: Single Responsibility, Separation of Concerns
    """

    @abstractmethod
    async def get_by_id(self, id: int) -> T | None:
        """Get entity by ID."""
        pass

    @abstractmethod
    async def get_all(self, **filters: Any) -> list[T]:
        """Get all entities matching filters."""
        pass

    @abstractmethod
    async def create(self, entity: T) -> T:
        """Create new entity."""
        pass

    @abstractmethod
    async def update(self, entity: T) -> T:
        """Update existing entity."""
        pass

    @abstractmethod
    async def delete(self, id: int) -> bool:
        """Delete entity by ID."""
        pass


# ============================================================================
# Service Interface
# ============================================================================


class IService(ABC):
    """
    Base interface for services.

    Services contain business logic and orchestrate
    repositories and other dependencies.

    Follows: Single Responsibility
    """

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the service."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Cleanup resources."""
        pass


# ============================================================================
# Event Handler Interface
# ============================================================================


@runtime_checkable
class IEventHandler(Protocol):
    """
    Protocol for event handlers.

    Enables loose coupling between components.
    """

    async def handle(self, event: dict) -> None:
        """Handle an event."""
        ...


# ============================================================================
# Cache Interface
# ============================================================================


class ICache(ABC, Generic[T]):
    """
    Cache interface for any cacheable data.

    Follows: Interface Segregation
    """

    @abstractmethod
    async def get(self, key: str) -> T | None:
        """Get cached value."""
        pass

    @abstractmethod
    async def set(self, key: str, value: T, ttl: int | None = None) -> None:
        """Set cached value."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete cached value."""
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Clear all cached values."""
        pass
