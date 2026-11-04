"""A word on the look list must never free a command that writes.

``_LOOK_SUBVERBS`` in ``divineos.core.gravity_classifier`` names the command words
the walk gate treats as pure reads. The exemption is by NAME: every CLI command
registered under one of those words inherits it. A human read each current
command's code before its word joined the list, but nothing stops a later
command from being registered as ``search`` or ``show`` and quietly writing
state while inheriting the exemption. This test reads the code of every such
command, and the core functions it calls, and fails if any of them writes.

What it cannot see is written down in
``docs/drafts/look_list_verbs_never_write_draft_2026-11-02.md``: call depth
beyond two core levels, dynamic dispatch, method calls on objects, and commands
registered outside ``src/divineos/cli/``.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pytest

from divineos.core.gravity_classifier import _LOOK_SUBVERBS

_SRC = Path(__file__).resolve().parents[1] / "src" / "divineos"
_CLI_DIR = _SRC / "cli"

# Two levels of core calls past the command itself. Deeper is not covered.
_MAX_CORE_DEPTH = 2

# Shaped statements, not bare words, so user-facing prose that happens to say
# "update" or "delete" in a print() does not read as SQL.
_SQL_WRITE = re.compile(
    r"\bINSERT\s+(?:OR\s+\w+\s+)?INTO\b|\bUPDATE\s+\S+\s+SET\b|\bDELETE\s+FROM\b"
    r"|\bREPLACE\s+INTO\b",
    re.IGNORECASE,
)
_WRITE_PREFIXES = (
    "record_",
    "store_",
    "save_",
    "file_",
    "set_",
    "delete_",
    "append_",
    "update_",
    "mark_",
    "add_",
    "write_",
)
# Names that start with a write prefix but only read or show. Exact names, so a
# real writer that shares a prefix still counts.
_READ_LOOKING = frozenset(
    {
        "set_title",
        "file_size",
        "file_name",
        "file_path",
        "file_exists",
        # In-memory builders and wrappers (argparse, click, rich, functools,
        # markupsafe), not stores.
        "add_argument",
        "add_argument_group",
        "add_row",
        "add_column",
        "add_text",
        "update_wrapper",
        "mark_safe",
    }
)
_WRITE_CALL_NAMES = frozenset(
    {
        "log_event",
        "write_text",
        "write_bytes",
        "eval",
        "exec",
        "executemany",
        "executescript",
        "unlink",
        "rmdir",
        "mkdir",
        "makedirs",
        "rmtree",
        "touch",
        "rename",
        "Popen",
    }
)
# Exact names on these modules: shutil copies, moves and deletes; os.remove
# deletes. shutil.which and shutil.get_terminal_size are reads, so shutil is
# listed by name and not as a whole module. (A bare ``.remove(`` is not matched:
# list.remove is an in-memory edit.)
_WRITE_MODULE_CALLS = {
    "shutil": frozenset(
        {
            "copy",
            "copy2",
            "copyfile",
            "copyfileobj",
            "copymode",
            "copystat",
            "copytree",
            "move",
            "rmtree",
            "chown",
            "make_archive",
            "unpack_archive",
        }
    ),
    "os": frozenset({"remove", "removedirs", "replace"}),
}
_WRITE_MODE_CHARS = set("wax+")

# Two lists, kept apart on purpose.
#
# _EXCUSED_FUNCTIONS: functions that LOOK like a write to a static reader but do
# not change state a reader would call state. Keyed by (file, function) and
# limited to the listed tokens, so a new kind of write added to an excused
# function still fails. One reason per entry.
_LAZY_SCHEMA = "creates or migrates its own tables on first open; idempotent, no user data changes"
_GIT_READ = (
    "runs only read-only git/gh subcommands (show, log, status, diff, rev-parse, view, list)"
)
_STORE_PATH = "calls store_path(), which only builds a filesystem path"
_LAZY_FOLDER = "creates its own parent folder on first open; no user data changes"
_SCRIPT = frozenset({"executescript("})
_MKDIR = frozenset({"mkdir("})
_SCHEMA = frozenset({".commit(", "sql-write", "executescript("})
_COMMIT = frozenset({".commit("})
_COMMIT_SCRIPT = _COMMIT | _SCRIPT
_SUBPROC = frozenset({"subprocess"})
_EXCUSED_FUNCTIONS: dict[tuple[str, str], tuple[str, frozenset[str]]] = {
    ("_schema.py", "init_watchmen_tables"): (_LAZY_SCHEMA, _COMMIT),
    ("affect.py", "init_affect_log"): (_LAZY_SCHEMA, _SCHEMA),
    ("andrew_correction_tracker.py", "_conn"): (_LAZY_SCHEMA, _COMMIT),
    ("andrew_given.py", "_conn"): (_LAZY_SCHEMA, _COMMIT),
    ("andrew_request_repeats.py", "_conn"): (_LAZY_SCHEMA, _COMMIT),
    ("bio.py", "init_bio_table"): (_LAZY_SCHEMA, _COMMIT),
    ("claim_store.py", "init_claim_tables"): (_LAZY_SCHEMA, _SCHEMA),
    # Folder creation, added when the detector learned mkdir. Keyed by file name
    # and function only, so a file named db.py is excused by name alone: a
    # weakness this list shares with every entry above.
    ("_hud_io.py", "_ensure_hud_dir"): (_LAZY_FOLDER, _MKDIR),
    ("_ledger_base.py", "get_connection"): (_LAZY_FOLDER, _MKDIR),
    ("andrew_correction_tracker.py", "_db_path"): (_LAZY_FOLDER, _MKDIR),
    ("andrew_given.py", "_db_path"): (_LAZY_FOLDER, _MKDIR),
    ("andrew_request_repeats.py", "_db_path"): (_LAZY_FOLDER, _MKDIR),
    ("council_walk.py", "_db_path"): (_LAZY_FOLDER, _MKDIR),
    ("db.py", "get_family_connection"): (_LAZY_FOLDER, _MKDIR),
    ("error_registry.py", "_ensure_home"): (_LAZY_FOLDER, _MKDIR),
    ("motivation.py", "_path_for"): (_LAZY_FOLDER, _MKDIR),
    ("must_read.py", "_dir"): (_LAZY_FOLDER, _MKDIR),
    ("vector_drawer.py", "_conn"): (_LAZY_FOLDER, _MKDIR),
    ("work_item_doorman.py", "_connect"): (_LAZY_SCHEMA, _SCRIPT),
    ("claim_store.py", "_migrate_add_confidence_basis"): (
        "one-time idempotent column backfill run by table setup",
        _SCHEMA,
    ),
    ("council_walk.py", "_conn"): (_LAZY_SCHEMA, _COMMIT_SCRIPT),
    ("decision_journal.py", "init_decision_journal"): (_LAZY_SCHEMA, _SCHEMA),
    ("findings_ledger.py", "_get_connection"): (_LAZY_SCHEMA, _COMMIT | _MKDIR),
    ("holding.py", "init_holding_table"): (_LAZY_SCHEMA, _COMMIT),
    ("memory.py", "init_memory_tables"): (_LAZY_SCHEMA, _SCHEMA),
    ("moral_compass.py", "init_compass"): (_LAZY_SCHEMA, _COMMIT),
    ("opinion_store.py", "init_opinion_table"): (_LAZY_SCHEMA, _COMMIT),
    ("queue.py", "_ensure_schema"): (_LAZY_SCHEMA, _COMMIT_SCRIPT),
    ("reach_check.py", "init_reach_tables"): (_LAZY_SCHEMA, _COMMIT),
    ("reflection_storage.py", "init_reflection_table"): (_LAZY_SCHEMA, _COMMIT),
    ("review_window.py", "_init"): (_LAZY_SCHEMA, _COMMIT),
    ("user_model.py", "init_user_model_table"): (_LAZY_SCHEMA, _COMMIT),
    ("build_flow.py", "judging_code_provenance"): (_GIT_READ, _SUBPROC),
    ("build_flow_commands.py", "_gh"): (_GIT_READ, _SUBPROC),
    ("build_flow_commands.py", "_git"): (_GIT_READ, _SUBPROC),
    ("build_flow_commands.py", "_judge_direction"): (_GIT_READ, _SUBPROC),
    ("build_flow_commands.py", "_judge_version_line"): (_GIT_READ, _SUBPROC),
    ("build_flow_commands.py", "_outside_the_flow_lines"): (_GIT_READ, _SUBPROC),
    ("build_flow_commands.py", "_run_git"): (_GIT_READ, _SUBPROC),
    ("push_choke.py", "_git"): (_GIT_READ, _SUBPROC),
    ("work_item_doorman.py", "dirty_code_paths"): (_GIT_READ, _SUBPROC),
    ("work_item_doorman.py", "head_commit_time"): (_GIT_READ, _SUBPROC),
    ("sibling_audit_rounds.py", "read_sibling_rounds"): (_STORE_PATH, frozenset({"store_path("})),
    ("sibling_council_walks.py", "read_sibling_walks"): (_STORE_PATH, frozenset({"store_path("})),
}

# _ALLOWED_WRITES: commands that REALLY write while sitting behind a look-list
# word. Not excused as harmless: each is a finding for a human to rule on
# (rename the command, drop the word from the list, or accept it). Listed so the
# test passes on main today and goes red the moment a NEW writer appears.
_ALLOWED_WRITES: dict[tuple[str, str], str] = {
    ("emergency_completion_commands.py::ec_group.status", "log_event("): (
        "FINDING: status on an expired arm appends EMERGENCY_COMPLETION_EXPIRED to the ledger"
    ),
    ("auto_cycle_commands.py::auto_cycle_group.status", "write_text("): (
        "FINDING: status reads the live context size, then stamps a heartbeat state file"
    ),
    ("auto_cycle_commands.py::auto_cycle_group.status", "open(write-mode)"): (
        "FINDING: the same heartbeat stamp appends a row to the heartbeat log"
    ),
    ("linkage_commands.py::linkage_group.status", "open(write-mode)"): (
        "FINDING: status records which family wall file the retriever resolved"
    ),
    ("work_item_commands.py::work_item_cmd.status", "sql-write"): (
        "FINDING: status closes a work item (UPDATE closed_at) when a commit has landed"
    ),
    ("emergency_completion_commands.py::ec_group.status", "unlink("): (
        "FINDING (new with the wider detector): status deletes the arm file when it is "
        "unreadable, malformed or expired"
    ),
    ("auto_cycle_commands.py::auto_cycle_group.status", "mkdir("): (
        "FINDING: the same heartbeat stamp creates its folder"
    ),
    ("linkage_commands.py::linkage_group.status", "mkdir("): (
        "FINDING: the same wall-resolution record creates its folder"
    ),
}


@dataclass(frozen=True)
class Command:
    key: str  # "file.py::group_expr.word", specific enough to name in a failure
    word: str
    path: Path
    node: ast.FunctionDef | ast.AsyncFunctionDef


@lru_cache(maxsize=None)
def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _registered_name(deco: ast.expr, func_name: str) -> str | None:
    """The Click name of a ``@x.command(...)`` decorator, or None if it is not one."""
    if not (
        isinstance(deco, ast.Call)
        and isinstance(deco.func, ast.Attribute)
        and deco.func.attr == "command"
    ):
        return None
    if deco.args and isinstance(deco.args[0], ast.Constant) and isinstance(deco.args[0].value, str):
        return deco.args[0].value
    for kw in deco.keywords:
        if kw.arg == "name" and isinstance(kw.value, ast.Constant):
            return str(kw.value.value)
    # Click's own default: the function name with underscores as dashes.
    return func_name.replace("_", "-")


def find_look_commands() -> list[Command]:
    found: list[Command] = []
    for path in sorted(_CLI_DIR.rglob("*.py")):
        for node in ast.walk(_parse(path)):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for deco in node.decorator_list:
                name = _registered_name(deco, node.name)
                if name in _LOOK_SUBVERBS:
                    group = ast.unparse(deco.func.value)  # type: ignore[attr-defined]
                    found.append(Command(f"{path.name}::{group}.{name}", name, path, node))
    return found


def _docstring_ids(tree: ast.AST) -> set[int]:
    ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = node.body
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                ids.add(id(body[0].value))
    return ids


def _call_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def _opens_for_writing(call: ast.Call) -> bool:
    mode: ast.expr | None = None
    # builtin open(path, mode) has mode second; Path.open(mode) has it first.
    index = 1 if isinstance(call.func, ast.Name) else 0
    if len(call.args) > index:
        mode = call.args[index]
    for kw in call.keywords:
        if kw.arg == "mode":
            mode = kw.value
    return (
        isinstance(mode, ast.Constant)
        and isinstance(mode.value, str)
        and bool(_WRITE_MODE_CHARS & set(mode.value))
    )


def _flat_text(node: ast.expr) -> str | None:
    """The text of an f-string or a ``+`` / ``%`` chain of strings, with ``{}`` where a
    value goes, so ``f"UPDATE {t} SET a = 1"`` reads as one statement. None if the
    node is neither."""
    if isinstance(node, ast.Constant):
        return node.value if isinstance(node.value, str) else None
    if isinstance(node, ast.JoinedStr):
        parts = []
        for v in node.values:
            parts.append(v.value if isinstance(v, ast.Constant) else "{}")
        return "".join(parts)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mod)):
        left, right = _flat_text(node.left), _flat_text(node.right)
        if left is None and right is None:
            return None
        return (left if left is not None else "{}") + (right if right is not None else "{}")
    return None


def find_writes(func: ast.AST, docstrings: set[int]) -> list[tuple[str, int]]:
    """(token, line) for every write-shaped thing in this function's own code."""
    hits: list[tuple[str, int]] = []
    for node in ast.walk(func):
        line = getattr(node, "lineno", 0)
        if isinstance(node, (ast.JoinedStr, ast.BinOp)):
            text = _flat_text(node)
            if text and _SQL_WRITE.search(text):
                hits.append(("sql-write", line))
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) not in docstrings and _SQL_WRITE.search(node.value):
                hits.append(("sql-write", line))
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in node.names]
            if isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module)
            if any(n.split(".")[0] == "subprocess" for n in names):
                hits.append(("subprocess", line))
        elif isinstance(node, ast.Name) and node.id == "subprocess":
            hits.append(("subprocess", line))
        elif isinstance(node, ast.Call):
            name = _call_name(node)
            if name is None:
                continue
            if name == "commit":
                hits.append((".commit(", line))
            elif name in _WRITE_CALL_NAMES:
                hits.append((f"{name}(", line))
            elif name == "open" and _opens_for_writing(node):
                hits.append(("open(write-mode)", line))
            elif (
                name == "system"
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "os"
            ):
                hits.append(("os.system", line))
            elif (
                isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id in _WRITE_MODULE_CALLS
                and name in _WRITE_MODULE_CALLS[node.func.value.id]
            ):
                hits.append((f"{node.func.value.id}.{name}(", line))
            elif name.startswith(_WRITE_PREFIXES) and name not in _READ_LOOKING:
                hits.append((f"{name}(", line))
    return hits


# --- resolving which core functions a function calls -------------------------


def _module_file(dotted: str) -> Path | None:
    base = _SRC.parent / Path(*dotted.split("."))
    for candidate in (base.with_suffix(".py"), base / "__init__.py"):
        if candidate.is_file():
            return candidate
    return None


def _module_name_of(path: Path) -> str:
    parts = list(path.relative_to(_SRC.parent).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _import_table(tree: ast.Module, own_module: str | None) -> dict[str, tuple[str, str | None]]:
    """local name -> (dotted module, attribute or None) for every import in the file,
    function-local ones included, because the CLI imports lazily."""
    table: dict[str, tuple[str, str | None]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    table[alias.asname] = (alias.name, None)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level and own_module:
                parts = own_module.split(".")
                base = ".".join(parts[: len(parts) - node.level] + ([base] if base else []))
            for alias in node.names:
                local = alias.asname or alias.name
                if _module_file(f"{base}.{alias.name}"):
                    table[local] = (f"{base}.{alias.name}", None)
                else:
                    table[local] = (base, alias.name)
    return table


def _defs_by_name(tree: ast.Module) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    return {
        n.name: n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _called_targets(
    func: ast.AST, path: Path, own_module: str | None
) -> tuple[list[tuple[Path, str]], list[tuple[Path, str]]]:
    """(same-file helpers, core functions) that this function calls by name."""
    tree = _parse(path)
    imports = _import_table(tree, own_module)
    local_defs = _defs_by_name(tree)
    same_file: list[tuple[Path, str]] = []
    core: list[tuple[Path, str]] = []
    for node in ast.walk(func):
        if not isinstance(node, ast.Call):
            continue
        target: tuple[str, str] | None = None
        if isinstance(node.func, ast.Name):
            name = node.func.id
            imported = imports.get(name)
            if imported and imported[1]:
                target = (imported[0], imported[1])
            elif name in local_defs:
                same_file.append((path, name))
                continue
        elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            mod = imports.get(node.func.value.id)
            if mod and mod[1] is None:
                target = (mod[0], node.func.attr)
        if target and target[0].startswith("divineos.core"):
            file = _module_file(target[0])
            if file:
                core.append((file, target[1]))
    return same_file, core


@dataclass(frozen=True)
class Hit:
    where: str  # call chain from the command down to the write
    token: str
    file: str
    func: str  # innermost function holding the write


def collect_writes(entry: ast.AST, path: Path) -> list[Hit]:
    """Writes in ``entry`` and in the functions it reaches.

    Same-file helpers belong to the command's own layer and cost no depth. Each
    hop into ``divineos.core`` costs one, up to ``_MAX_CORE_DEPTH``.
    """
    results: list[Hit] = []
    seen: set[tuple[Path, str]] = set()

    def visit(func: ast.AST, fpath: Path, depth: int, label: str) -> None:
        here = getattr(func, "name", "<command>")
        for token, line in find_writes(func, _docstring_ids(_parse(fpath))):
            results.append(Hit(f"{label} ({fpath.name}:{line})", token, fpath.name, here))
        own_module = _module_name_of(fpath) if depth else None
        same_file, core = _called_targets(func, fpath, own_module)
        for spath, name in same_file:
            if (spath, name) not in seen:
                seen.add((spath, name))
                visit(_defs_by_name(_parse(spath))[name], spath, depth, f"{label} > {name}")
        if depth >= _MAX_CORE_DEPTH:
            return
        for cpath, name in core:
            if (cpath, name) in seen:
                continue
            seen.add((cpath, name))
            target = _defs_by_name(_parse(cpath)).get(name)
            if target is not None:
                visit(target, cpath, depth + 1, f"{label} > core:{name}")

    visit(entry, path, 0, "command")
    return results


# --- the tests ---------------------------------------------------------------

_COMMANDS = find_look_commands()

# The five words PR #726 added plus a few older ones, by command key, so a
# renamed file or a broken scan cannot silently drop them.
_KNOWN_COMMANDS = (
    "claim_commands.py::claims_group.search",
    "decision_commands.py::decisions_group.search",
    "journal_commands.py::journal_group.search",
    "audit_commands.py::audit_group.list-clean",
    "audit_commands.py::audit_group.surprises",
    "audit_commands.py::audit_group.unknown-unknown-rate",
    "compass_commands.py::compass_group.spectrums",
    "prereg_commands.py::prereg_group.overdue",
    "prereg_commands.py::prereg_group.windows",
)


def test_scan_found_a_real_number_of_commands():
    # An empty or truncated scan would pass the no-writes test vacuously.
    assert len(_COMMANDS) >= 60, f"only {len(_COMMANDS)} look-list commands found"
    keys = {c.key for c in _COMMANDS}
    missing = [k for k in _KNOWN_COMMANDS if k not in keys]
    assert not missing, f"scan lost known commands: {missing}"


def test_every_look_word_has_at_least_one_command():
    # A word with no command behind it is either a typo on the list or a scan
    # that cannot see how that command is registered.
    seen = {c.word for c in _COMMANDS}
    assert seen >= _LOOK_SUBVERBS, f"no command found for: {sorted(_LOOK_SUBVERBS - seen)}"


def test_checker_flags_a_known_writer():
    # record_self_audit_prediction calls log_event. Treated as if it sat behind a
    # look-list word, the checker must call it a write; if it does not, a clean
    # result below means nothing.
    path = _SRC / "core" / "operating_loop" / "unknown_unknown_surface.py"
    writer = _defs_by_name(_parse(path))["record_self_audit_prediction"]
    assert "log_event(" in {h.token for h in collect_writes(writer, path)}


def test_checker_follows_a_call_into_core(tmp_path: Path):
    # A command whose own body is clean but which calls the known writer in core:
    # the walk must descend one level and see the write there.
    probe = tmp_path / "probe_cli.py"
    probe.write_text(
        "from divineos.core.operating_loop.unknown_unknown_surface import "
        "record_self_audit_prediction\n"
        "def cmd():\n    record_self_audit_prediction()\n",
        encoding="utf-8",
    )
    findings = collect_writes(_defs_by_name(_parse(probe))["cmd"], probe)
    assert any(
        h.token == "log_event(" and "core:record_self_audit_prediction" in h.where for h in findings
    )


@pytest.mark.parametrize(
    "snippet,token",
    [
        ("def f(c):\n    c.execute('INSERT INTO t VALUES (1)')", "sql-write"),
        ("def f(c):\n    c.execute('update t set a = 1')", "sql-write"),
        ("def f(c):\n    c.execute('DELETE FROM t')", "sql-write"),
        ("def f(c):\n    c.execute('REPLACE INTO t VALUES (1)')", "sql-write"),
        ("def f(c):\n    c.commit()", ".commit("),
        ("def f(p):\n    p.write_text('x')", "write_text("),
        ("def f(p):\n    p.write_bytes(b'x')", "write_bytes("),
        ("def f(p):\n    open(p, 'w')", "open(write-mode)"),
        ("def f(p):\n    p.open('a')", "open(write-mode)"),
        ("def f():\n    import subprocess", "subprocess"),
        ("def f():\n    os.system('x')", "os.system"),
        ("def f(x):\n    eval(x)", "eval("),
        ("def f(x):\n    exec(x)", "exec("),
        ("def f():\n    log_event('x')", "log_event("),
        ("def f():\n    record_thing()", "record_thing("),
        ("def f():\n    append_row()", "append_row("),
        ("def f():\n    update_row()", "update_row("),
        ("def f():\n    mark_done()", "mark_done("),
        ("def f():\n    add_item()", "add_item("),
        ("def f():\n    write_state()", "write_state("),
        ("def f(c):\n    c.executemany('x', [])", "executemany("),
        ("def f(c):\n    c.executescript('x')", "executescript("),
        ("def f(p):\n    p.unlink()", "unlink("),
        ("def f(p):\n    p.mkdir()", "mkdir("),
        ("def f(p):\n    p.rename('x')", "rename("),
        ("def f():\n    shutil.rmtree('x')", "rmtree("),
        ("def f():\n    shutil.copy('a', 'b')", "shutil.copy("),
        ("def f():\n    shutil.move('a', 'b')", "shutil.move("),
        ("def f():\n    shutil.copytree('a', 'b')", "shutil.copytree("),
        ("def f():\n    os.remove('x')", "os.remove("),
        ("def f():\n    Popen(['x'])", "Popen("),
        ("def f(c, t):\n    c.execute(f'UPDATE {t} SET a = 1')", "sql-write"),
        ("def f(c, t):\n    c.execute(f'INSERT INTO {t} VALUES (1)')", "sql-write"),
        ("def f(c, t):\n    c.execute(f'DELETE FROM {t}')", "sql-write"),
        ("def f(c, t):\n    c.execute('UPDATE ' + t + ' SET a = 1')", "sql-write"),
        ("def f(c, t):\n    c.execute('UPDATE %s SET a = 1' % t)", "sql-write"),
    ],
)
def test_each_write_shape_is_detected(snippet: str, token: str):
    tree = ast.parse(snippet)
    assert token in {t for t, _ in find_writes(tree.body[0], _docstring_ids(tree))}


@pytest.mark.parametrize(
    "snippet",
    [
        "def f(p):\n    '''INSERT INTO is only a docstring'''\n    return open(p)",
        "def f(p):\n    return open(p, 'r')",
        "def f(c):\n    c.execute('SELECT * FROM t')",
        "def f():\n    print('click to update the view')",
        "def f(w):\n    w.set_title('x')",
        "def f(p):\n    return file_size(p)",
        "def f(xs):\n    xs.remove(1)",
        "def f(c, t):\n    c.execute(f'SELECT * FROM {t}')",
        "def f(t):\n    print(f'update {t} to see more')",
        "def f():\n    return shutil.which('git')",
        "def f():\n    return shutil.get_terminal_size()",
        "def f(p):\n    p.add_argument('--x')",
        "def f(t):\n    t.add_row('a', 'b')",
        "def f(t):\n    t.add_column('a')",
        "def f(w, g):\n    update_wrapper(w, g)",
    ],
)
def test_reads_are_not_flagged(snippet: str):
    tree = ast.parse(snippet)
    assert find_writes(tree.body[0], _docstring_ids(tree)) == []


def test_look_list_commands_never_write():
    violations: set[str] = set()
    used_commands: set[tuple[str, str]] = set()
    used_excuses: set[tuple[str, str]] = set()
    for cmd in _COMMANDS:
        for hit in collect_writes(cmd.node, cmd.path):
            excuse = _EXCUSED_FUNCTIONS.get((hit.file, hit.func))
            if excuse and hit.token in excuse[1]:
                used_excuses.add((hit.file, hit.func))
            elif (cmd.key, hit.token) in _ALLOWED_WRITES:
                used_commands.add((cmd.key, hit.token))
            else:
                violations.add(f"{cmd.key}: {hit.token} in {hit.where}")
    assert not violations, (
        "A command behind a look-list word writes state, so its word frees a write "
        "from the walk gate. Rename the command, drop the word from _LOOK_SUBVERBS "
        "(a human decision), or add it to _ALLOWED_WRITES / _EXCUSED_FUNCTIONS with a "
        "one-line reason:\n  " + "\n  ".join(sorted(violations))
    )
    stale = (set(_ALLOWED_WRITES) - used_commands) | (set(_EXCUSED_FUNCTIONS) - used_excuses)
    assert not stale, f"allowlist entries that no longer match a write: {sorted(stale)}"
