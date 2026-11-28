"""The dark-surface list is read from a named commit's own tree, in its own process.

The board used to read the list from whatever checkout it ran in, which is never the pull
request's code. Comparing a branch with main needs each tree evaluated for real. The control
is a tiny real git repo whose tree says exactly what its dark list is.
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


def _repo(tmp_path, dark_names):
    repo = tmp_path / "repo"
    pkg = repo / "src" / "divineos" / "core"
    pkg.mkdir(parents=True)
    (repo / "src" / "divineos" / "__init__.py").write_text("")
    (pkg / "__init__.py").write_text("")
    (pkg / "surface_bridge.py").write_text("")
    (pkg / "surface_registry.py").write_text(
        f"def dark_surfaces(package='divineos.core'):\n    return {dark_names!r}\n"
    )
    _git(repo, "init", "-q")
    _git(repo, *_ID, "add", "-A")
    _git(repo, *_ID, "commit", "-q", "-m", "x")
    return repo, _head(repo)


def test_it_reads_the_dark_list_of_the_named_commit_not_of_the_checkout(tmp_path):
    repo, sha = _repo(tmp_path, ["fake_one", "fake_two"])
    assert dark_at(repo, sha, tmp_path / "cache") == ["fake_one", "fake_two"]


def test_two_commits_give_two_answers(tmp_path):
    repo, sha_a = _repo(tmp_path, ["a"])
    (repo / "src" / "divineos" / "core" / "surface_registry.py").write_text(
        "def dark_surfaces(package='divineos.core'):\n    return ['b']\n"
    )
    _git(repo, *_ID, "commit", "-q", "-am", "y")
    sha_b = _head(repo)
    cache = tmp_path / "cache"
    assert dark_at(repo, sha_a, cache) == ["a"]
    assert dark_at(repo, sha_b, cache) == ["b"]


def test_the_answer_is_cached_by_commit(tmp_path):
    repo, sha = _repo(tmp_path, ["x"])
    cache = tmp_path / "cache"
    assert dark_at(repo, sha, cache) == ["x"]
    assert (cache / f"{sha}.json").exists()
    # a commit's tree never changes, so its cache entry is the answer
    (cache / f"{sha}.json").write_text('["from_cache"]')
    assert dark_at(repo, sha, cache) == ["from_cache"]


def test_an_unknown_commit_is_could_not_read_never_empty(tmp_path):
    repo, _ = _repo(tmp_path, [])
    assert dark_at(repo, "0" * 40, tmp_path / "cache") is None


def test_a_tree_whose_registry_fails_is_could_not_read_never_empty(tmp_path):
    repo, _ = _repo(tmp_path, [])
    (repo / "src" / "divineos" / "core" / "surface_registry.py").write_text(
        "raise RuntimeError('x')\n"
    )
    _git(repo, *_ID, "commit", "-q", "-am", "z")
    assert dark_at(repo, _head(repo), tmp_path / "cache") is None


def test_the_probe_can_find_a_case_it_should_find(tmp_path):
    # control for the instrument: a tree with dark names must not read as empty
    repo, sha = _repo(tmp_path, ["present"])
    assert dark_at(repo, sha, tmp_path / "cache") != []
