"""The check that keeps one reader of him finds a private one, and says where the home is."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "check_no_private_his_reader", ROOT / "scripts" / "check_no_private_his_reader.py"
)
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


def _plant(tmp_path, monkeypatch, body: str) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "private.py").write_text(body, encoding="utf-8")
    monkeypatch.setattr(check, "ROOT", tmp_path)
    monkeypatch.setattr(check, "SEARCH_ROOTS", (tmp_path / "src",))


def test_a_private_reader_is_found(tmp_path, monkeypatch, capsys):
    _plant(tmp_path, monkeypatch, 'if rec.get("type") == "last-prompt":\n    pass\n')
    assert check.main() == 1
    out = capsys.readouterr().out
    assert "src/private.py:1" in out and check.HOME in out


def test_a_comment_naming_a_shape_is_not_a_reader(tmp_path, monkeypatch):
    _plant(tmp_path, monkeypatch, "# he may arrive as a queued_command or a last-prompt\n")
    assert check.main() == 0


def test_the_real_tree_has_no_private_reader():
    assert check.offenders() == []
