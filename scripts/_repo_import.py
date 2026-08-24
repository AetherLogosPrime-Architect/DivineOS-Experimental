"""Make ``import divineos`` mean THIS checkout, for scripts run under bare python.

Import this before importing divineos::

    import _repo_import  # noqa: F401  -- must precede any divineos import

    from divineos.core.something import thing

WHY THIS EXISTS
---------------
Two checkouts of this project live on one machine and share one Python
installation, so exactly one of them wins the editable install. Anything run
with bare ``python`` gets that winner, whichever it is.

The failure is silent and it looks like success. On 2026-08-13,
``scripts/check_test_cli_linkage.py`` ran inside the pre-commit gate under bare
python and printed "OK: 42 test-referenced commands all register" on every
commit -- while comparing the OTHER checkout's command registrations against
this checkout's tests. A green line, a real check, the wrong object.

That is the same bug Aletheia caught on 2026-07-15, when guardrail edits
appeared to pass 141 tests that pytest had run against a stale install from a
different worktree. It was fixed for pytest (``pythonpath = ["src"]`` plus the
fail-loud check in ``tests/conftest.py``) and for the CLI (the wrapper's sealed
dispatch). It never reached ``scripts/``.

ONE HELPER, NOT A THIRD COPY
----------------------------
Two scripts already carry a hand-rolled ``sys.path.insert``. Pasting it into
three more is how this repo acquired twelve separate bash resolvers that
disagree with each other -- the cleanup list's job five. Copy number three is
where divergence begins, so this is the single place.

It works as a plain ``import _repo_import`` because python puts a script's own
directory first on the path before anything else runs.

FAIL LOUD, NOT FAIL SAFE
------------------------
If divineos is already imported from somewhere else by the time this runs, the
path insert is too late -- the module object is cached and the insert changes
nothing while looking like it worked. That case raises rather than warns,
because a warning here would be printed into exactly the kind of output nobody
reads, which is the disease this whole file is treating.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = _REPO_ROOT / "src"


def _already_imported_from_elsewhere() -> str | None:
    """Return the offending path if divineos is loaded from another tree."""
    mod = sys.modules.get("divineos")
    origin = getattr(mod, "__file__", None) if mod is not None else None
    if origin is None:
        return None
    try:
        Path(origin).resolve().relative_to(_SRC.resolve())
    except ValueError:
        return origin
    return None


_stale = _already_imported_from_elsewhere()
if _stale is not None:
    raise ImportError(
        "divineos was already imported from another checkout:\n"
        f"    {_stale}\n"
        f"    expected somewhere under {_SRC}\n"
        "Import _repo_import BEFORE any divineos import. Inserting the path "
        "afterwards silently does nothing -- the module object is already cached, "
        "and the script would keep running against the other tree while looking fine."
    )

if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
