"""The full-suite door reads what runs, not the word.

``divineos`` record commands (learn, decide, ...) carry text that nothing
executes, so the word pytest inside their arguments is data. Everything that CAN
execute stays fail-closed. Companion to ``tests/test_full_suite_by_hand.py``,
which is unchanged.

The exemption is by NAME, so ``test_no_record_command_executes_its_text`` reads
the code of every command in the set and what it calls in ``divineos.core`` and
fails if any of it can run its text. Borrows the call-following approach of
``tests/test_look_list_verbs_never_write.py`` (draft PR 755) without depending
on it.

What the pin cannot see: call depth beyond two core levels, dynamic dispatch
(getattr, callbacks, method calls on objects), commands registered outside
``src/divineos/cli/``. Green means nothing executable was found within those
limits, not that nothing exists.
"""

from __future__ import annotations

import ast
from functools import cache
from pathlib import Path

import pytest

from divineos.core.full_suite_by_hand import _RECORD_COMMANDS, decide

HEADER = "THE FULL SUITE IS THE PUSH'S JOB"

# One example per command in the set, the word inside its quoted text.
RECORD_EXAMPLES = [
    'divineos learn "pytest tests/ is the push\'s job"',
    'divineos decide "stop running pytest by hand" --why "pytest tests/ takes 20 minutes"',
    'divineos claim "the door refuses pytest in notes" --tier 3',
    'divineos feel -v 0.5 -a 0.4 --dom 0.5 -d "annoyed at pytest false alarm"',
    'divineos journal save "wrote about pytest today"',
    'divineos compass-ops observe humility -p 0.1 -e "mentioned pytest honestly"',
    'divineos prereg file "door" --claim "pytest word is data" --success "x" --falsifier "y"',
    'divineos prereg assess prereg-abc --outcome SUCCESS --actor aletheia --notes "pytest ok"',
    'divineos goal add "narrow the pytest door"',
    # Unquoted, and after a cd, are still just text for a record command.
    "divineos learn pytest",
    'cd /repo && divineos learn "pytest tests/"',
]

REFUSED_STILL = [
    # The same text after a program that is not in the set.
    'note "pytest tests/ is the push\'s job"',
    'divineos ask "pytest tests/"',
    'divineos reflect-ops save "pytest tests/"',
    'divineos-other learn "pytest"',
    # Not the bare program: a runner in front of it.
    'timeout 5 divineos learn "pytest"',
    'xargs divineos learn "pytest"',
    # Hidden strings stay fail-closed.
    "echo pytest | sh",
    'bash -c "divineos reflection-note pytest"',
    'bash -c "divineos learn pytest"',
    "python -c \"import subprocess; subprocess.run('pytest')\"",
    "python -c 'import pytest; pytest.main()'",
    '(divineos learn "pytest")',
    '{ divineos learn "pytest"; }',
    # A substitution inside a record command's quotes DOES execute.
    'divineos learn "$(pytest)"',
    'divineos learn "`pytest`"',
    'divineos learn "${PYTEST:-pytest}"',
    'divineos learn "<(pytest)"',
    # A second command chained after a record command is its own segment.
    'divineos learn "ok" && pytest',
    'divineos learn "ok"; pytest tests/',
    'divineos learn "pytest" | sh',
    'divineos learn "pytest" | xargs sh -c',
    # Plain runs.
    "pytest tests/",
    "pytest",
    "python -m pytest",
]

PASSED_STILL = [
    "pytest tests/test_a.py -q",
    "pytest tests/test_a.py tests/test_b.py::test_c -x",
    "python -m pytest tests/test_full_suite_by_hand.py -q",
]


def test_the_set_is_what_was_verified_and_no_more():
    # reflection-note is named in the task but has no Click function anywhere
    # in this repository, so its safety cannot be checked and it is not here.
    assert _RECORD_COMMANDS == frozenset(
        {
            ("learn",),
            ("decide",),
            ("claim",),
            ("feel",),
            ("journal", "save"),
            ("compass-ops", "observe"),
            ("prereg", "file"),
            ("prereg", "assess"),
            ("goal", "add"),
        }
    )


@pytest.mark.parametrize("cmd", RECORD_EXAMPLES)
def test_record_commands_pass_with_the_word_in_their_text(cmd):
    assert decide(cmd) is None


def test_every_command_in_the_set_has_an_example():
    covered = {
        key
        for key in _RECORD_COMMANDS
        if any(f"divineos {' '.join(key)} " in ex for ex in RECORD_EXAMPLES)
    }
    assert covered == set(_RECORD_COMMANDS)


@pytest.mark.parametrize("cmd", REFUSED_STILL)
def test_everything_that_can_execute_is_still_refused(cmd):
    reason = decide(cmd)
    assert reason and HEADER in reason, cmd


@pytest.mark.parametrize("cmd", PASSED_STILL)
def test_named_test_files_still_pass(cmd):
    assert decide(cmd) is None


# --- the refusal says which rule fired --------------------------------------


def test_a_word_refusal_names_the_rule_and_the_way_out():
    reason = decide('note "pytest tests/ is the push\'s job"')
    assert "cannot prove is only text" in reason
    assert "divineos learn" in reason  # the one way out
    assert "Run the tests for what you changed" not in reason
    assert "15-20 mins" in reason


def test_a_hidden_string_gets_the_word_rule_not_the_run_advice():
    reason = decide('bash -c "echo pytest"')
    assert "cannot prove is only text" in reason
    assert "Run the tests for what you changed" not in reason


def test_a_real_pytest_run_keeps_the_original_advice(tmp_path, monkeypatch):
    import divineos.core.full_suite_by_hand as fs

    monkeypatch.setattr(fs, "changed_tests", lambda repo: ["tests/test_a.py"])
    reason = decide("pytest tests/ -q", repo=tmp_path)
    assert "pytest tests/test_a.py -q" in reason
    assert "cannot prove is only text" not in reason


def test_a_real_run_with_nothing_mapped_still_says_so(tmp_path, monkeypatch):
    import divineos.core.full_suite_by_hand as fs

    monkeypatch.setattr(fs, "changed_tests", lambda repo: [])
    assert "No changed file maps to a test file" in decide("pytest", repo=tmp_path)


# --- the way out named is true for how the word arrived ----------------------


def test_a_wrapped_run_with_files_named_is_not_told_to_name_the_files():
    reason = decide('bash -c "pytest tests/test_a.py -q"')
    assert reason and HEADER in reason
    assert "not the problem" in reason  # the files it named are not what was refused
    assert "unwrapped" in reason
    assert "name the test files" not in reason


def test_a_wrapper_without_files_does_not_claim_the_files_were_named():
    reason = decide('bash -c "echo pytest"')
    assert "not the problem" not in reason
    assert "unwrapped" in reason


def test_a_gh_body_is_told_to_use_a_body_file():
    reason = decide('gh pr create --title t --body "ran pytest tests/test_a.py ok"')
    assert reason and HEADER in reason
    assert "--body-file" in reason
    assert "name the test files" not in reason
    assert "divineos learn" in reason


def test_a_heredoc_body_is_text_not_a_run():
    reason = decide("cat <<'EOF' | git commit -F -\nran pytest\nEOF")
    assert reason and HEADER in reason
    assert "here-document" in reason
    assert "Write tool" in reason
    assert "This runs every test in the house" not in reason


def test_a_run_before_a_heredoc_is_still_a_run(tmp_path, monkeypatch):
    import divineos.core.full_suite_by_hand as fs

    monkeypatch.setattr(fs, "changed_tests", lambda repo: ["tests/test_a.py"])
    reason = decide("pytest -q && cat <<'EOF'\nnotes\nEOF", repo=tmp_path)
    assert "pytest tests/test_a.py -q" in reason


def test_a_pipe_into_a_shell_is_told_not_to_pipe():
    reason = decide("echo pytest | sh")
    assert reason and "piped" in reason
    assert "name the test files" not in reason


@pytest.mark.parametrize(
    "cmd",
    [
        './.direnv/python-3.13.11/Scripts/divineos.exe learn "pytest tests/"',
        '/usr/bin/divineos learn "pytest tests/"',
        'C:/x/DIVINEOS.EXE decide "stop running pytest" --why "slow"',
        '.venv/bin/divineos goal add "narrow the pytest door"',
    ],
)
def test_a_record_command_is_exempt_whatever_the_spelling_of_the_program(cmd):
    assert decide(cmd) is None


@pytest.mark.parametrize(
    "cmd",
    [
        '/usr/bin/divineos ask "pytest tests/"',
        './divineos-other learn "pytest"',
        '/x/divineos.exe learn "$(pytest)"',
    ],
)
def test_the_exemption_by_program_name_does_not_widen_what_is_exempt(cmd):
    reason = decide(cmd)
    assert reason and HEADER in reason


@pytest.mark.parametrize(
    "cmd",
    [
        'python -m divineos learn "pytest tests/"',
        'python3 -m divineos decide "stop running pytest" --why "slow"',
        'C:\\x\\divineos.exe learn "pytest tests/"',
        'C:\\x\\Scripts\\DIVINEOS.EXE goal add "narrow the pytest door"',
    ],
)
def test_honest_record_commands_by_python_m_or_an_unquoted_windows_path_pass(cmd):
    """The same program, spelled another way. shlex ate the backslashes of an
    unquoted Windows path, and python -m divineos hid the program behind python."""
    assert decide(cmd) is None


@pytest.mark.parametrize(
    "cmd",
    [
        'python -m divineos ask "pytest tests/"',
        'python -m other learn "pytest"',
        'python -m divineos learn "$(pytest)"',
        'C:\\x\\divineos-other.exe learn "pytest"',
    ],
)
def test_python_m_and_windows_paths_do_not_widen_the_exemption(cmd):
    reason = decide(cmd)
    assert reason and HEADER in reason


@pytest.mark.parametrize(
    "cmd",
    [
        "echo $((1+2)); pytest -q",
        "echo $((2)) && pytest tests/",
        "echo $(( 1 )); pytest",
        "echo $((1<<2)); pytest -q",
        "echo $((1+2))\npytest tests/",
    ],
)
def test_a_line_the_splitter_cannot_cut_is_not_waved_through_by_its_first_word(cmd):
    """Arithmetic expansion made split_shell_segments give up, and the door then
    judged the whole line by its first word, echo, a reader. The run after it was
    never looked at."""
    reason = decide(cmd)
    assert reason and HEADER in reason, cmd


@pytest.mark.parametrize(
    "cmd",
    [
        "echo $((1+2)); pytest tests/test_a.py -q",
        "echo $((1+2))",
        "echo $((1+2)) && ls tests/",
        'echo $((1+2)) && git commit -m "pytest tests/ belongs to the push"',
    ],
)
def test_the_same_uncuttable_line_with_no_whole_suite_run_still_passes(cmd):
    """Control: the crude cut must not start refusing honest lines."""
    assert decide(cmd) is None, cmd


# --- the pin: no command in the set executes its text ------------------------

_SRC = Path(__file__).resolve().parents[1] / "src" / "divineos"
_CLI_DIR = _SRC / "cli"
_MAX_CORE_DEPTH = 2
_FUNCS = (ast.FunctionDef, ast.AsyncFunctionDef)


@cache
def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _first_str(deco: ast.Call) -> str | None:
    if deco.args and isinstance(deco.args[0], ast.Constant) and isinstance(deco.args[0].value, str):
        return deco.args[0].value
    for kw in deco.keywords:
        if kw.arg == "name" and isinstance(kw.value, ast.Constant):
            return str(kw.value.value)
    return None


def _decorators(node: ast.AST, attr: str):
    for deco in node.decorator_list:
        if (
            isinstance(deco, ast.Call)
            and isinstance(deco.func, ast.Attribute)
            and deco.func.attr == attr
        ):
            yield deco


def find_click_functions(key: tuple[str, ...]) -> list[tuple[Path, ast.AST]]:
    """The Click function(s) registered for this tuple of command words."""
    found: list[tuple[Path, ast.AST]] = []
    for path in sorted(_CLI_DIR.rglob("*.py")):
        tree = _parse(path)
        funcs = [n for n in ast.walk(tree) if isinstance(n, _FUNCS)]
        if len(key) == 1:
            for fn in funcs:
                for deco in _decorators(fn, "command"):
                    owner = ast.unparse(deco.func.value)
                    name = _first_str(deco) or fn.name.replace("_", "-")
                    if owner == "cli" and name == key[0]:
                        found.append((path, fn))
            continue
        groups = {
            fn.name
            for fn in funcs
            for deco in _decorators(fn, "group")
            if (_first_str(deco) or fn.name.replace("_", "-")) == key[0]
            and ast.unparse(deco.func.value) == "cli"
        }
        for fn in funcs:
            for deco in _decorators(fn, "command"):
                name = _first_str(deco) or fn.name.replace("_", "-")
                if ast.unparse(deco.func.value) in groups and name == key[1]:
                    found.append((path, fn))
    return found


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
    """local name -> (dotted module, attribute or None); function-local imports
    included, because the CLI imports lazily."""
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


def _defs_by_name(tree: ast.Module) -> dict[str, ast.AST]:
    return {n.name: n for n in ast.walk(tree) if isinstance(n, _FUNCS)}


def _called_targets(func: ast.AST, path: Path, own_module: str | None):
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
            imported = imports.get(node.func.id)
            if imported and imported[1]:
                target = (imported[0], imported[1])
            elif node.func.id in local_defs:
                same_file.append((path, node.func.id))
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


_OS_RUNNERS = {"system", "popen", "execv", "execve", "execl", "execlp", "execvp", "startfile"}


def find_executors(func: ast.AST) -> list[tuple[str, int]]:
    """(token, line) for each way this function's own code can run its text."""
    hits: list[tuple[str, int]] = []
    for node in ast.walk(func):
        line = getattr(node, "lineno", 0)
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in node.names]
            if isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module)
            for n in names:
                if n.split(".")[0] in ("subprocess", "shlex"):
                    hits.append((n.split(".")[0], line))
        elif isinstance(node, ast.Name) and node.id in ("subprocess", "shlex"):
            hits.append((node.id, line))
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in ("eval", "exec", "compile"):
                hits.append((f"{node.func.id}(", line))
            elif (
                isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "os"
                and (node.func.attr in _OS_RUNNERS or node.func.attr.startswith("spawn"))
            ):
                hits.append((f"os.{node.func.attr}", line))
    return hits


def collect_executors(entry: ast.AST, path: Path) -> list[tuple[str, str, int]]:
    """(chain, token, line). Same-file helpers cost no depth; each hop into
    divineos.core costs one, up to _MAX_CORE_DEPTH."""
    results: list[tuple[str, str, int]] = []
    seen: set[tuple[Path, str]] = set()

    def visit(func: ast.AST, fpath: Path, depth: int, label: str) -> None:
        for token, line in find_executors(func):
            results.append((f"{label} ({fpath.name}:{line})", token, line))
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


@pytest.mark.parametrize("key", sorted(_RECORD_COMMANDS))
def test_no_record_command_executes_its_text(key):
    functions = find_click_functions(key)
    assert functions, f"no Click function found for divineos {' '.join(key)}"
    problems: list[str] = []
    for path, fn in functions:
        problems += [f"{chain}: {tok}" for chain, tok, _ in collect_executors(fn, path)]
    assert not problems, (
        f"divineos {' '.join(key)} can execute something; remove it from _RECORD_COMMANDS:\n"
        + "\n".join(problems)
    )


# --- controls: the walker can find what it should ----------------------------


def test_the_walker_finds_a_command_registered_under_a_group():
    paths = {p.name for p, _ in find_click_functions(("journal", "save"))}
    assert "journal_commands.py" in paths


def test_the_walker_finds_a_top_level_command_with_a_default_name():
    paths = {p.name for p, _ in find_click_functions(("learn",))}
    assert "knowledge_commands.py" in paths


def test_the_walker_follows_a_call_into_core():
    path, entry = find_click_functions(("journal", "save"))[0]
    _, core = _called_targets(entry, path, None)
    assert any("memory_journal" in str(p) for p, _ in core)


@pytest.mark.parametrize(
    "snippet, token",
    [
        ("import subprocess\nsubprocess.run(text)", "subprocess"),
        ("import os\nos.system(text)", "os.system"),
        ("eval(text)", "eval("),
        ("exec(text)", "exec("),
        ("import shlex\nargs = shlex.split(text)", "shlex"),
        ("import os\nos.popen(text)", "os.popen"),
    ],
)
def test_each_executing_shape_is_caught(snippet, token):
    body = "\n".join("    " + ln for ln in snippet.splitlines())
    tree = ast.parse(f"def f(text):\n{body}\n")
    assert token in {t for t, _ in find_executors(tree)}


def test_a_plain_function_is_not_flagged():
    tree = ast.parse("def f(text):\n    return text.strip().upper()\n")
    assert find_executors(tree) == []
