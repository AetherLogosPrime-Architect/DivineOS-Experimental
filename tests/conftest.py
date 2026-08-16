"""
Pytest configuration and fixtures for DivineOS tests.
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

# Add tests directory to path
sys.path.insert(0, str(Path(__file__).parent))


def _verify_divineos_import_path(config: pytest.Config) -> None:
    """Fail-loud check that the imported `divineos` package lives in
    THIS worktree, not a stale editable install pointing elsewhere.

    Aletheia audit round-a1e7f4c92b6d, 2026-07-15 (Aria's automation
    ask to Andrew: "automate the verification so I don't have to
    remember"). Prior failure: guardrail edits appeared to pass 141
    tests, but pytest imported `divineos` from a different worktree's
    stale editable install. Tests were false-verifying — passing
    against code that didn't contain the changes under test.

    Pairs with `pythonpath = ["src"]` in pyproject.toml: the config
    line makes local src/ preferred; this check verifies that
    preference actually took effect. Both together mean the
    silently-wrong-code failure mode cannot recur without one of two
    independent gates firing loud.

    Skip if `DIVINEOS_ALLOW_IMPORT_MISMATCH=1` is set in env — for
    the rare case of intentionally testing an installed package
    against a checked-out test suite (not our workflow, but the
    escape hatch exists for principled use).
    """
    if os.environ.get("DIVINEOS_ALLOW_IMPORT_MISMATCH") == "1":
        return
    try:
        import divineos
    except ImportError:
        # Nothing to check — the missing-package error will surface
        # on the first test that imports divineos.
        return
    imported_path = Path(divineos.__file__).resolve()
    worktree_src = (Path(__file__).parent.parent / "src" / "divineos" / "__init__.py").resolve()
    if imported_path != worktree_src:
        raise pytest.UsageError(
            f"divineos imported from {imported_path}, "
            f"but this worktree is at {worktree_src}. "
            f"Tests would run against the wrong code — silently. "
            f"Fix: `pip install -e .` from THIS worktree, or set "
            f"DIVINEOS_ALLOW_IMPORT_MISMATCH=1 to bypass (only for "
            f"principled cross-worktree-install testing)."
        )


def pytest_configure(config: pytest.Config) -> None:
    """Set basetemp to a project-local directory to avoid Windows permissions issues."""
    # Cap xdist workers at 16 when xdist is loaded (Aletheia FLAG 2, 2026-07-02).
    # Prior placement in pyproject addopts broke pytest invocations from
    # minimal environments where xdist wasn't installed. Setting the option
    # here only when xdist is active preserves the cap in production runs
    # while keeping non-xdist paths clean.
    #
    # Root cause of the original cap: unrestricted -n auto on a 16-core+HT
    # box resolved to 40 workers, each ~1.5GB, demanding 60GB on a 31GB
    # system. Andrew's call: cap at 16.
    _verify_divineos_import_path(config)

    if config.pluginmanager.hasplugin("xdist"):
        current = getattr(config.option, "maxprocesses", None)
        if current is None:
            config.option.maxprocesses = 16

    if config.option.basetemp is None:
        pytest_tmp = Path(__file__).parent.parent / "tmp" / "pytest"
        # Use a unique subdir per run to avoid stale file collisions after crashes
        local_tmp = pytest_tmp / f"run-{os.getpid()}"
        local_tmp.mkdir(parents=True, exist_ok=True)
        config.option.basetemp = str(local_tmp)

        # Clean up old runs (keep last 3) to prevent unbounded disk growth.
        # Without this, each run leaves ~189MB of temp databases — 27 runs = 4.6GB.
        # Aria 2026-06-23: ignore_errors=True was silently swallowing
        # PermissionError on Windows (read-only git pack files in test
        # fixtures). 46K files accumulated as a result. The onerror handler
        # chmods read-only files writable before retrying the unlink — same
        # fix Aria tested on her side and shipped to her conftest.
        try:
            import stat

            def _force_writable(func, path, _exc_info):  # noqa: ARG001
                """Make read-only file writable, retry the unlink. Windows
                refuses os.unlink on read-only files; git pack-objects in
                test fixtures are marked read-only by standard git behavior."""
                os.chmod(path, stat.S_IWRITE)
                func(path)

            old_runs = sorted(
                [d for d in pytest_tmp.iterdir() if d.is_dir() and d.name.startswith("run-")],
                key=lambda p: p.stat().st_mtime,
            )
            for stale in old_runs[:-3]:
                shutil.rmtree(stale, onerror=_force_writable)
        except OSError:
            pass


@pytest.fixture(scope="session")
def git_template_repo(tmp_path_factory) -> Path:
    """One initialized .git directory per session.

    Tests that need a fresh repo should copy from this instead of
    running another `git init`. Avoids the Windows MSYS2 DLL-init
    race that occasionally fires STATUS_DLL_INIT_FAILED when many
    git processes spawn in quick succession.
    """
    from _git_test_helpers import _build_template_repo

    template = tmp_path_factory.mktemp("git_template_repo")
    _build_template_repo(template, bare=False)
    return template


@pytest.fixture(scope="session")
def git_template_bare_repo(tmp_path_factory) -> Path:
    """Bare-repo counterpart for tests that need an `upstream.git`."""
    from _git_test_helpers import _build_template_repo

    template = tmp_path_factory.mktemp("git_template_bare")
    _build_template_repo(template, bare=True)
    return template


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path):
    """Give every test its own fresh database so tests never interfere with each other.

    Also isolates DIVINEOS_HOME (per-user state dir for files like
    checkpoint_state.json) so xdist workers don't stomp on each other's
    counters under -n auto.

    Fable 5 audit fix 2026-06-09: also pops DIVINEOS_SESSION_ID. Since
    initialize_session() reuses an existing env-var session, any test
    that didn't call clear_session() was leaking its session id into
    every subsequent test in the same xdist worker — a flaky-test class
    same as the May race-condition finding, new instance. Popping
    both at setup and teardown guarantees each test starts with a
    fresh session id namespace.
    """
    db_path = tmp_path / "test_ledger.db"
    home_path = tmp_path / "divineos_home"
    home_path.mkdir(parents=True, exist_ok=True)

    # Clear leaked SESSION_ID BEFORE assigning the fresh DB so a stale
    # session id can't reach the new ledger.
    os.environ.pop("DIVINEOS_SESSION_ID", None)
    os.environ["DIVINEOS_DB"] = str(db_path)
    os.environ["DIVINEOS_HOME"] = str(home_path)
    os.environ["DIVINEOS_DISABLE_AUTO_REMEDIATE"] = "1"

    from divineos.core.ledger import init_db

    init_db()
    yield
    os.environ.pop("DIVINEOS_DB", None)
    os.environ.pop("DIVINEOS_HOME", None)
    os.environ.pop("DIVINEOS_DISABLE_AUTO_REMEDIATE", None)
    os.environ.pop("DIVINEOS_SESSION_ID", None)


@pytest.fixture
def temp_test_dir():
    """Provide a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


def _real_repo_git_config() -> Path | None:
    """Path to the ACTUAL repository's .git/config, or None if undiscoverable.

    Worktrees keep a `.git` file pointing at the shared repo, so this
    resolves through to the one config every worktree writes to.
    """
    start = Path(__file__).resolve().parent
    for candidate in (start, *start.parents):
        dot_git = candidate / ".git"
        if dot_git.is_dir():
            cfg = dot_git / "config"
            return cfg if cfg.exists() else None
        if dot_git.is_file():
            # worktree: "gitdir: <path>" -> commondir holds the shared config
            try:
                target = Path(dot_git.read_text(encoding="utf-8").split(":", 1)[1].strip())
            except (OSError, IndexError):
                return None
            if not target.is_absolute():
                target = (candidate / target).resolve()
            common = target / "commondir"
            if common.exists():
                try:
                    rel = common.read_text(encoding="utf-8").strip()
                except OSError:
                    return None
                target = (target / rel).resolve()
            cfg = target / "config"
            return cfg if cfg.exists() else None
    return None


@pytest.fixture(autouse=True)
def _real_repo_config_tripwire():
    """Fail the test that writes into the REAL repository's git config.

    Found 2026-08-08. Symptom: `core.bare` intermittently flipped to true
    on the working repository, which breaks every git command in every
    worktree ("this operation must be run in a work tree") for hours. The
    live config also carried `user.email = test@test` — an identity that
    exists only in tests/, so test writes had been landing on the real
    repo for an unknown stretch.

    Mechanism: `git init <path>` CREATES the directory before initializing
    it. Several tests run `git init ... "$DIR" >/dev/null 2>&1` and never
    check the exit status (the same discard-the-status shape this repo
    hunts everywhere else). When init fails partway — the documented MSYS2
    DLL-init race that `_git_test_helpers.safe_git_init` retries around —
    the directory exists, `cd` into it succeeds, and every subsequent git
    command walks UP the tree until it finds a real repository, then
    writes there.

    This does not prevent the write; it makes it LOUD and attributable.
    Silent config corruption discovered hours later becomes a named test
    failing at the moment it happens. If the config is undiscoverable the
    fixture stays out of the way rather than guessing — but that is
    "could not check", not "checked and clean", so it says so.
    """
    cfg = _real_repo_git_config()
    before = None
    if cfg is not None:
        try:
            before = cfg.read_bytes()
        except OSError:
            before = None
    yield
    if cfg is None or before is None:
        return
    try:
        after = cfg.read_bytes()
    except OSError:
        return
    if after != before:
        try:
            cfg.write_bytes(before)
            restored = "restored"
        except OSError:
            restored = "COULD NOT RESTORE — repo config is still modified"
        pytest.fail(
            f"This test wrote to the REAL repository git config ({cfg}).\n"
            f"Tests must operate on temp repos only. Config was {restored}.\n"
            "Likely cause: an unchecked `git init` left a directory without a\n"
            "repo in it, so a later git command discovered the real repo by\n"
            "walking up the tree. Check the exit status of every git init."
        )
