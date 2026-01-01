"""
Dependency Injection Container.

Manages service dependencies and enables loose coupling
following the Dependency Inversion Principle.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, TypeVar, Generic, cast
from functools import lru_cache

from rsw.interfaces import IDataProvider, IStateStore, IStrategyCalculator, ICache
from rsw.runtime_config import get_config

T = TypeVar("T")


@dataclass
class Container:
    """
    Simple dependency injection container.
    
    Follows: Dependency Inversion Principle
    
    Usage:
        container = Container()
        container.register(IDataProvider, OpenF1Client)
        provider = container.resolve(IDataProvider)
    """
    
    _factories: dict[type, Callable[..., Any]] = field(default_factory=dict)
    _singletons: dict[type, Any] = field(default_factory=dict)
    _singleton_types: set[type] = field(default_factory=set)
    
    def register(
        self,
        interface: type[T],
        factory: Callable[..., T],
        singleton: bool = False,
    ) -> None:
        """
        Register a factory for an interface.
        
        Args:
            interface: The abstract interface type
            factory: Callable that creates the implementation
            singleton: If True, only one instance is created
        """
        self._factories[interface] = factory
        if singleton:
            self._singleton_types.add(interface)
    
    def resolve(self, interface: type[T]) -> T:
        """
        Resolve an interface to its implementation.
        
        Args:
            interface: The interface type to resolve
            
        Returns:
            Instance of the implementation
            
        Raises:
            KeyError: If interface is not registered
        """
        if interface not in self._factories:
            raise KeyError(f"No factory registered for {interface.__name__}")
        
        # Return singleton if exists
        if interface in self._singleton_types:
            if interface not in self._singletons:
                self._singletons[interface] = self._factories[interface]()
            return cast(T, self._singletons[interface])
        
        # Create new instance
        return cast(T, self._factories[interface]())
    
    def reset(self) -> None:
        """Reset all singletons (useful for testing)."""
        self._singletons.clear()


# ============================================================================
# Application Dependencies
# ============================================================================

@dataclass
class AppDependencies:
    """
    Application-wide dependencies.
    
    Centralizes all dependencies for easy injection.
    Follows: Single Responsibility, Dependency Inversion
    """
    
    data_provider: IDataProvider
    state_store: IStateStore
    strategy_calculator: IStrategyCalculator | None = None
    cache: ICache | None = None


def create_dependencies() -> AppDependencies:
    """
    Factory function to create application dependencies.
    
    This is the composition root where implementations
    are bound to interfaces.
    
    Follows: Dependency Inversion (depend on abstractions)
    """
    from rsw.ingest import OpenF1Client
    from rsw.state.store import RaceStateStore
    from rsw.services.strategy_service import StrategyService
    
    config = get_config()
    
    # Create implementations
    data_provider = OpenF1Client()
    state_store = RaceStateStore()
    strategy_calculator = StrategyService(config.strategy)
    
    return AppDependencies(
        data_provider=cast(IDataProvider, data_provider),
        state_store=cast(IStateStore, state_store),
        strategy_calculator=strategy_calculator,
    )


# ============================================================================
# FastAPI Dependency Injection
# ============================================================================

_container: Container | None = None


def get_container() -> Container:
    """Get or create the DI container."""
    global _container
    if _container is None:
        _container = Container()
        _register_dependencies(_container)
    return _container


def _register_dependencies(container: Container) -> None:
    """Register all dependencies in the container."""
    from typing import cast, Callable, Any
    from rsw.ingest import OpenF1Client
    from rsw.state.store import RaceStateStore
    
    container.register(IDataProvider, cast(Callable[..., IDataProvider], OpenF1Client), singleton=True) # type: ignore[type-abstract]
    container.register(IStateStore, cast(Callable[..., IStateStore], RaceStateStore), singleton=True) # type: ignore[type-abstract]


# FastAPI dependency functions
async def get_data_provider() -> IDataProvider:
    """FastAPI dependency for data provider."""
    return get_container().resolve(IDataProvider) # type: ignore[type-abstract]


async def get_state_store() -> IStateStore:
    """FastAPI dependency for state store."""
    return get_container().resolve(IStateStore) # type: ignore[type-abstract]
