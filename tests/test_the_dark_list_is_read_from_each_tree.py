"""The dark-surface list is read from a named commit's own tree, in its own process.

The board used to read the list from whatever checkout it ran in, which is never the pull
request's code. Comparing a branch with main needs each tree evaluated for real. The control
is a tiny real git repo whose tree says exactly what its dark list is.

Two false-clean holes Aria found in her cold read of #884 (2026-11-28), both pinned here:
a clean answer must never be believed from a file on disk, and a tree where a module fails to
import must read as could-not-read, because the registry skips such a module and a newly dark
surface that cannot import would otherwise read clean.
"""

import subprocess

from divineos.cli.build_flow_commands import dark_at

_ID = ["-c", "user.email=t@t", "-c", "user.name=t"]


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _head(repo):
    return subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()


def _registry(dark_names, failed=()):
    return (
        f"def dark_surfaces(package='divineos.core'):\n    return {list(dark_names)!r}\n\n"
        f"def discover(package='divineos.core'):\n    return {list(failed)!r}\n"
    )


def _repo(tmp_path, dark_names, failed=()):
    repo = tmp_path / "repo"
    pkg = repo / "src" / "divineos" / "core"
    pkg.mkdir(parents=True)
    (repo / "src" / "divineos" / "__init__.py").write_text("")
    (pkg / "__init__.py").write_text("")
    (pkg / "surface_bridge.py").write_text("")
    (pkg / "surface_registry.py").write_text(_registry(dark_names, failed))
    _git(repo, "init", "-q")
    _git(repo, *_ID, "add", "-A")
    _git(repo, *_ID, "commit", "-q", "-m", "x")
    return repo, _head(repo)


def _recommit(repo, registry_text):
    (repo / "src" / "divineos" / "core" / "surface_registry.py").write_text(registry_text)
    _git(repo, *_ID, "commit", "-q", "-am", "y")
    return _head(repo)


def test_it_reads_the_dark_list_of_the_named_commit_not_of_the_checkout(tmp_path):
    repo, sha = _repo(tmp_path, ["fake_one", "fake_two"])
    assert dark_at(repo, sha, tmp_path / "cache") == ["fake_one", "fake_two"]


def test_two_commits_give_two_answers(tmp_path):
    repo, sha_a = _repo(tmp_path, ["a"])
    sha_b = _recommit(repo, _registry(["b"]))
    cache = tmp_path / "cache"
    assert dark_at(repo, sha_a, cache) == ["a"]
    assert dark_at(repo, sha_b, cache) == ["b"]


def test_a_dark_answer_is_cached_by_commit(tmp_path):
    repo, sha = _repo(tmp_path, ["x"])
    cache = tmp_path / "cache"
    assert dark_at(repo, sha, cache) == ["x"]
    assert (cache / f"{sha}.json").exists()


def test_a_clean_answer_is_never_written_to_the_disk_cache(tmp_path):
    # the clean direction is the dangerous one: a file saying [] would be final
    repo, sha = _repo(tmp_path, [])
    cache = tmp_path / "cache"
    assert dark_at(repo, sha, cache) == []
    assert not (cache / f"{sha}.json").exists()


def test_a_poisoned_clean_entry_on_disk_is_ignored_and_the_tree_is_read_again(tmp_path):
    repo, sha = _repo(tmp_path, ["really_dark"])
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / f"{sha}.json").write_text("[]")  # a false clean, written by hand
    assert dark_at(repo, sha, cache) == ["really_dark"]


def test_an_unknown_commit_is_could_not_read_never_empty(tmp_path):
    repo, _ = _repo(tmp_path, [])
    assert dark_at(repo, "0" * 40, tmp_path / "cache") is None


def test_a_tree_whose_registry_fails_is_could_not_read_never_empty(tmp_path):
    repo, _ = _repo(tmp_path, [])
    sha = _recommit(repo, "raise RuntimeError('x')\n")
    assert dark_at(repo, sha, tmp_path / "cache") is None


def test_a_tree_where_a_module_fails_to_import_is_could_not_read_not_clean(tmp_path):
    # dark_surfaces() skips a module whose import raises, so a newly dark surface that cannot
    # import reads clean; the registry's own discover() names the failure and we must believe it
    repo, sha = _repo(tmp_path, [], failed=["memory_journal: ImportError: no module named x"])
    cache = tmp_path / "cache"
    assert dark_at(repo, sha, cache) is None
    assert not (cache / f"{sha}.json").exists()


def test_the_probe_can_find_a_case_it_should_find(tmp_path):
    # control for the instrument: a tree with dark names must not read as empty
    repo, sha = _repo(tmp_path, ["present"])
    assert dark_at(repo, sha, tmp_path / "cache") != []
