"""Pytest plugin for scripts/cutaway.py: cut the code out from under a test, see if the test notices.

WHY. A test that stays green when the code it names is destroyed is not testing that code.
The static audit (check_test_substance.py) asks whether a test is CAPABLE of failing; this
asks whether it DEPENDS on the product. Found on 2026-10-07: 22 tests that passed when the
command they test crashed, because "exit code is not zero" and "no warning printed" are
both true of a crash.

HOW. Every function and method in the target modules has its body replaced, IN PLACE, by one
that counts a hit and raises. In place matters: a test that did `from pkg.mod import f`
holds the function object, so swapping the module attribute would not reach it. The swap is
live ONLY while a test body runs, never during fixtures, or every test would die in setup
and say nothing about itself.

Per test, in the call phase only:
  CONNECTED     red, and the cut code was reached          -> the test depends on it
  DISCONNECTED  green, and the cut code was never reached  -> the test never touched it
  SWALLOWED     green, but the cut code WAS reached        -> the test hid the failure
  OTHER-RED     red, cut code never reached                -> failed for another reason

WHAT IT CANNOT SEE, stated because a quiet gap reads as coverage:
  - Code that runs in a child process (the driver labels those OUT-OF-PROCESS, not fake).
  - Product consumed through a fixture: a fixture builds the object before the cut, and the
    test body then only inspects it. Such a test reads DISCONNECTED and may be an honest
    check of data shape. DISCONNECTED means "a person should read this", never "fake".
  - Whether a connected test checks the RIGHT thing. It measures dependence, not correctness.

Each of these blind spots was a confident wrong number first (a re-exported function hid its
real home; scripts loaded with importlib and never registered were invisible; one script
loaded under two names; click commands defined inside register() are not module attributes).
The tests in tests/test_cutaway.py are those cases.
"""

from __future__ import annotations

import builtins
import importlib
import inspect
import json
import os
import sys
import types

import pytest

TARGETS = [n for n in os.environ.get("CUTAWAY_NAMES", "").split(",") if n]
OUT = os.environ.get("CUTAWAY_OUT", "")
REPO = os.environ.get("CUTAWAY_REPO", "")
ARM = bool(os.environ.get("CUTAWAY_ARM"))
CLI_MODULE = os.environ.get("CUTAWAY_CLI_MODULE", "")  # e.g. "divineos.cli": its click group
PRODUCT_PREFIX = os.environ.get("CUTAWAY_PREFIX", "")
EXTRA_ROOTS = [r for r in os.environ.get("CUTAWAY_EXTRA_ROOTS", "").split(",") if r]


class Cutaway(Exception):
    pass


# The stub's globals are the PRODUCT module's, not this file's, so it finds its counter and
# its exception through builtins.
builtins._CUTAWAY_HITS = [0]  # type: ignore[attr-defined]
builtins._CutawayErr = Cutaway  # type: ignore[attr-defined]


def _stub(*_a, **_k):
    _CUTAWAY_HITS[0] += 1  # noqa: F821 - resolved from builtins on purpose
    raise _CutawayErr("cut away")  # noqa: F821


_STUBS: dict[int, types.CodeType] = {0: _stub.__code__}


def _stub_code_with(free_vars: int) -> types.CodeType:
    """A stub code object carrying the same number of free variables as what it replaces.

    __code__ assignment demands equal free-variable counts, and CLI commands are mostly
    closures defined inside register(), so a closure must be cuttable too.
    """
    if free_vars not in _STUBS:
        names = [f"_f{i}" for i in range(free_vars)]
        src = "def _outer():\n" + "".join(f"    {n} = None\n" for n in names)
        src += "    def _inner(*a, **k):\n        " + ", ".join(names) + "\n"
        src += "        _CUTAWAY_HITS[0] += 1\n        raise _CutawayErr('cut away')\n"
        src += "    return _inner\n"
        ns: dict = {}
        exec(compile(src, "<cutaway-stub>", "exec"), ns)  # noqa: S102 - generated, no input
        _STUBS[free_vars] = ns["_outer"]().__code__
    return _STUBS[free_vars]


ARMED: list[tuple[types.FunctionType, types.CodeType]] = []
_ARMED_IDS: set[int] = set()
report: dict = {"functions": 0, "skipped": 0, "modules": [], "click_callbacks": 0, "unresolved": []}


def _register(fn) -> None:
    """Remember fn so it can be cut while a test body runs. Nothing is swapped yet."""
    if not isinstance(fn, types.FunctionType) or id(fn) in _ARMED_IDS:
        return
    if fn.__code__ in set(_STUBS.values()):
        return
    _ARMED_IDS.add(id(fn))
    ARMED.append((fn, fn.__code__))
    report["functions"] += 1


def _register_click(obj) -> None:
    """Click commands keep their body in .callback; groups hold more commands."""
    callback = getattr(obj, "callback", None)
    if isinstance(callback, types.FunctionType):
        _register(callback)
        report["click_callbacks"] += 1
    for sub in (getattr(obj, "commands", None) or {}).values():
        _register_click(sub)


def _register_module(mod: types.ModuleType) -> None:
    name = mod.__name__
    if name == __name__:
        # The plugin sits in scripts/, a folder it scans as product. Cutting its own
        # _stub_code_with made every test after the first fail in setup, and the first
        # full sweep (2026-10-08) reported "nothing weak" over 3,256 unmeasured tests.
        return
    for attr, obj in list(vars(mod).items()):
        if attr.startswith("__"):
            continue
        if isinstance(obj, types.FunctionType) and obj.__module__ == name:
            _register(obj)
        elif hasattr(obj, "callback") and getattr(obj.callback, "__module__", "") == name:
            _register_click(obj)
        elif inspect.isclass(obj) and getattr(obj, "__module__", "") == name:
            for cname, cobj in list(vars(obj).items()):
                if cname.startswith("__"):
                    continue
                if isinstance(cobj, (staticmethod, classmethod)):
                    _register(cobj.__func__)
                elif isinstance(cobj, types.FunctionType):
                    _register(cobj)
                elif isinstance(cobj, property) and cobj.fget:
                    _register(cobj.fget)
    report["modules"].append(name)


def _home_module(dotted: str) -> types.ModuleType | None:
    """The module that DEFINES what `dotted` names, or None.

    `pkg.name` may be a module, or a function or class re-exported by pkg: cut it where it
    is defined, not where it is re-exported (the first sweep called 172 of 181 tests cut off
    for want of this).
    """
    try:
        mod = importlib.import_module(dotted)
    except Exception:  # noqa: BLE001 - "not a module" is the ordinary case here
        parent, _, leaf = dotted.rpartition(".")
        if not parent:
            return None
        try:
            obj = getattr(importlib.import_module(parent), leaf)
        except Exception:  # noqa: BLE001
            return None
        home = getattr(obj, "__module__", "") or ""
        if PRODUCT_PREFIX and home.split(".")[0] == PRODUCT_PREFIX:
            try:
                return importlib.import_module(home)
            except Exception:  # noqa: BLE001
                return None
        return None
    return None if hasattr(mod, "__path__") else mod  # a package has no code of its own


def _under(path: str, root: str) -> bool:
    return path.replace("\\", "/").lower().startswith(root.replace("\\", "/").lower() + "/")


def pytest_collection_finish(session):
    for dotted in TARGETS:
        mod = _home_module(dotted)
        if mod is not None:
            _register_module(mod)
        elif not dotted.count("."):
            report["unresolved"].append(dotted)

    if ARM and REPO:
        roots = [os.path.join(REPO, r) for r in EXTRA_ROOTS]
        # Product that lives outside the package (scripts, hooks, other folders) and that the
        # test file loaded itself.
        for name, mod in list(sys.modules.items()):
            path = getattr(mod, "__file__", None) or ""
            if path and any(_under(path, r) for r in roots) and name not in TARGETS:
                _register_module(mod)
        # Script modules loaded with importlib and NEVER put in sys.modules live only in the
        # test module's own globals.
        for tmod in list(sys.modules.values()):
            if not _under(getattr(tmod, "__file__", None) or "", os.path.join(REPO, "tests")):
                continue
            for val in list(vars(tmod).values()):
                if isinstance(val, types.ModuleType):
                    vpath = getattr(val, "__file__", None) or ""
                    if any(_under(vpath, r) for r in roots):
                        _register_module(val)

    if CLI_MODULE and any(t.startswith(CLI_MODULE) for t in TARGETS):
        # Commands are mostly defined inside register() as closures, so they live in the
        # click group and not as module attributes.
        try:
            group = getattr(importlib.import_module(CLI_MODULE), "cli")
            _register_click(group)
        except Exception as exc:  # noqa: BLE001
            report["unresolved"].append(f"{CLI_MODULE}: {exc}")


def _arm() -> None:
    for fn, original in ARMED:
        try:
            fn.__code__ = _stub_code_with(len(original.co_freevars))
        except ValueError:
            report["skipped"] += 1


def _disarm() -> None:
    for fn, original in ARMED:
        fn.__code__ = original


RESULTS: dict[str, dict] = {}


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    item._cutaway_before = _CUTAWAY_HITS[0]  # noqa: F821
    if ARM:
        try:
            _arm()
        except BaseException:
            # The test body never ran, so whatever red follows says nothing about the product.
            item._cutaway_arm_failed = True
            _disarm()
            raise
    try:
        yield
    finally:
        if ARM:
            _disarm()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if call.when == "call" and getattr(item, "_cutaway_arm_failed", False):
        RESULTS[item.nodeid] = {"outcome": "setup-arm-failed", "hits": 0}
    elif call.when == "call":
        hits = _CUTAWAY_HITS[0] - getattr(item, "_cutaway_before", 0)  # noqa: F821
        RESULTS[item.nodeid] = {"outcome": rep.outcome, "hits": hits}
    elif call.when == "setup" and rep.outcome != "passed":
        RESULTS[item.nodeid] = {"outcome": "setup-" + rep.outcome, "hits": 0}


def pytest_sessionfinish(session):
    if OUT:
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump({"results": RESULTS, "report": report}, f)
