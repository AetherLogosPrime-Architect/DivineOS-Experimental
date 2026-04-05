"""Compatibility layer for hypothesis when not installed.

Provides dummy implementations of hypothesis decorators and strategies
so tests can be collected and skipped gracefully when hypothesis is missing.
"""

try:
    from hypothesis import given, strategies as st, settings, HealthCheck

    HAS_HYPOTHESIS = True
except ImportError:
    HAS_HYPOTHESIS = False

    # Provide dummy decorators and strategies for when hypothesis is not installed
    class DummyStrategy:
        def __call__(self, *args, **kwargs):
            return self

    st = type(
        "st",
        (),
        {
            "text": DummyStrategy(),
            "integers": DummyStrategy(),
            "dictionaries": DummyStrategy(),
            "just": DummyStrategy(),
        },
    )()

    def given(*args, **kwargs):
        def decorator(func):
            return func

        return decorator

    def settings(*args, **kwargs):
        def decorator(func):
            return func

        return decorator

    class HealthCheck:
        too_slow = None


__all__ = ["HAS_HYPOTHESIS", "given", "st", "settings", "HealthCheck"]
