"""Error handling and recovery for DivineOS integration points.

Provides centralized error handling, retry logic, and recovery mechanisms
for all 5 integration points.
"""

import time
from typing import Any, Callable, Optional, TypeVar, Tuple
from functools import wraps
import sqlite3
from loguru import logger

_EH_ERRORS = (ImportError, sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)

T = TypeVar("T")


class IntegrationError(Exception):
    """Base exception for integration errors."""

    pass


class RetryableError(IntegrationError):
    """Error that can be retried."""

    pass


class FatalError(IntegrationError):
    """Error that cannot be recovered."""

    pass


class ErrorHandler:
    """Centralized error handling for integration points."""

    # Retry configuration
    MAX_RETRIES = 3
    INITIAL_BACKOFF = 0.1  # seconds
    MAX_BACKOFF = 5.0  # seconds
    BACKOFF_MULTIPLIER = 2.0

    # Retryable error types
    RETRYABLE_ERRORS = (
        TimeoutError,
        ConnectionError,
        OSError,
        RetryableError,
    )

    @staticmethod
    def with_retry(
        func: Callable[..., T],
        max_retries: int = MAX_RETRIES,
        backoff_multiplier: float = BACKOFF_MULTIPLIER,
    ) -> Callable[..., T]:
        """Decorator to add retry logic to a function.

        Args:
            func: Function to wrap
            max_retries: Maximum number of retries
            backoff_multiplier: Multiplier for exponential backoff

        Returns:
            Wrapped function with retry logic
        """

        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            backoff = ErrorHandler.INITIAL_BACKOFF
            last_error = None
            func_name = getattr(func, "__name__", str(func))

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except ErrorHandler.RETRYABLE_ERRORS as e:
                    last_error = e
                    if attempt < max_retries:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed for {func_name}: {e}. "
                            f"Retrying in {backoff:.2f}s..."
                        )
                        time.sleep(backoff)
                        backoff = min(backoff * backoff_multiplier, ErrorHandler.MAX_BACKOFF)
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed for {func_name}: {e}")
                except FatalError as e:
                    logger.error(f"Fatal error in {func_name}: {e}")
                    raise
                except Exception as e:
                    logger.error(f"Unexpected error in {func_name}: {e}")
                    raise

            if last_error:
                raise last_error

            # This should not be reached, but satisfy type checker
            raise RuntimeError(f"Unexpected state in retry wrapper for {func_name}")

        return wrapper

    @staticmethod
    def handle_integration_point_error(
        integration_point: str,
        error: Exception,
        context: Optional[dict[str, Any]] = None,
    ) -> Tuple[bool, str]:
        """Handle error from an integration point.

        Args:
            integration_point: Name of the integration point
            error: The error that occurred
            context: Additional context about the error

        Returns:
            Tuple of (should_retry, error_message)
        """
        if context is None:
            context = {}

        error_msg = f"Error in {integration_point}: {str(error)}"
        logger.error(error_msg, extra={"context": context})

        # Determine if error is retryable
        if isinstance(error, ErrorHandler.RETRYABLE_ERRORS):
            return True, error_msg
        elif isinstance(error, FatalError):
            return False, error_msg
        else:
            # Unknown error - don't retry
            return False, error_msg

    @staticmethod
    def log_error_with_context(
        error: Exception,
        context: dict[str, Any],
        integration_point: str,
    ) -> None:
        """Log error with full context for debugging.

        Args:
            error: The error that occurred
            context: Context information
            integration_point: Name of the integration point
        """
        logger.error(
            f"Integration error in {integration_point}",
            extra={
                "error_type": type(error).__name__,
                "error_message": str(error),
                "context": context,
                "integration_point": integration_point,
            },
        )


def retry_on_error(max_retries: int = 3):
    """Decorator for retry logic.

    Args:
        max_retries: Maximum number of retries

    Returns:
        Decorator function
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        return ErrorHandler.with_retry(func, max_retries=max_retries)

    return decorator


class RecoveryStrategy:
    """Recovery strategies for different error scenarios."""

    @staticmethod
    def fallback_to_default(
        func: Callable[..., T],
        default_value: T,
        error_types: tuple = (Exception,),
    ) -> Callable[..., T]:
        """Fallback to default value on error.

        Args:
            func: Function to wrap
            default_value: Value to return on error
            error_types: Tuple of error types to catch

        Returns:
            Wrapped function
        """

        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except error_types as e:
                logger.warning(f"Error in {func.__name__}, using default: {e}")
                return default_value

        return wrapper

    @staticmethod
    def circuit_breaker(
        func: Callable[..., T],
        failure_threshold: int = 5,
        timeout: float = 60.0,
    ) -> Callable[..., T]:
        """Circuit breaker pattern for error handling.

        Args:
            func: Function to wrap
            failure_threshold: Number of failures before opening circuit
            timeout: Time to wait before attempting to close circuit

        Returns:
            Wrapped function
        """
        state: dict[str, Any] = {"failures": 0, "last_failure_time": 0.0, "open": False}

        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Check if circuit should be closed
            if state["open"]:
                if time.time() - state["last_failure_time"] > timeout:
                    logger.info(f"Attempting to close circuit for {func.__name__}")
                    state["open"] = False
                    state["failures"] = 0
                else:
                    raise FatalError(f"Circuit breaker open for {func.__name__}")

            try:
                result = func(*args, **kwargs)
                state["failures"] = 0
                return result
            except Exception:
                state["failures"] += 1
                state["last_failure_time"] = time.time()

                if state["failures"] >= failure_threshold:
                    state["open"] = True
                    logger.error(
                        f"Circuit breaker opened for {func.__name__} "
                        f"after {state['failures']} failures"
                    )

                raise

        return wrapper
