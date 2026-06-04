"""Compatibility layer for hypothesis when not installed.

Provides dummy implementations of hypothesis decorators and strategies
so tests can be collected and skipped gracefully when hypothesis is missing.
"""

try:
    from hypothesis import HealthCheck, given, settings
    from hypothesis import strategies as st

    HAS_HYPOTHESIS = True
except ImportError:
    HAS_HYPOTHESIS = False

    # Provide dummy decorators and strategies for when hypothesis is not installed.
    #
    # FAIL-LOUD on missing strategies (Aletheia 2026-06-04): the prior shim
    # exposed only 4 strategies (text/integers/dictionaries/just). Property
    # tests using st.lists / st.booleans / st.floats / st.sampled_from would
    # AttributeError at import time, silently dropping those files from
    # pytest collection — CI would report green-on-fewer-tests-than-expected.
    # The fix: enumerate every strategy the test suite uses so collection
    # succeeds, AND surface any future-missing strategy via __getattr__ that
    # raises a clear error naming the gap (not a silent AttributeError that
    # gets eaten by the import machinery).
    class DummyStrategy:
        def __call__(self, *args, **kwargs):
            return self

    _DUMMY = DummyStrategy()

    class _StShim:
        # Enumerated strategies — every name the test suite imports must live
        # here. Add new ones as tests use them; do NOT rely on __getattr__ to
        # silently paper over missing strategies, because that returns success
        # when the test should fail-loud.
        text = _DUMMY
        integers = _DUMMY
        dictionaries = _DUMMY
        just = _DUMMY
        lists = _DUMMY
        booleans = _DUMMY
        floats = _DUMMY
        sampled_from = _DUMMY
        one_of = _DUMMY
        none = _DUMMY
        binary = _DUMMY
        composite = _DUMMY

        def __getattr__(self, name: str):  # type: ignore[no-untyped-def]
            raise AttributeError(
                f"hypothesis_compat.st has no strategy named {name!r}. "
                f"Hypothesis is not installed and the compat shim does not "
                f"enumerate this strategy. Either install hypothesis "
                f"(pip install hypothesis) or add {name} to the _StShim class "
                f"in tests/hypothesis_compat.py so pytest collection does not "
                f"silently skip files that reference it."
            )

    st = _StShim()

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
