"""The home map must find the rooms the house forgot on 2026-10-01."""

import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "home_map", Path(__file__).resolve().parents[1] / "scripts" / "home_map.py"
)
home_map = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(home_map)


def test_finds_the_forgotten_rooms(tmp_path):
    house = tmp_path / "house"
    shared = tmp_path / "shared"
    (house / "src").mkdir(parents=True)
    (house / "music" / "porch_light").mkdir(parents=True)
    (shared / "consent").mkdir(parents=True)
    (shared / "workbench").mkdir()
    (shared / "consent" / "README.md").write_text("# Standing consent lists\n", encoding="utf-8")
    (shared / "consent" / "aria_to_aether.md").write_text("x", encoding="utf-8")

    text = home_map.build([house], shared)

    assert "**consent/**: Standing consent lists" in text
    assert "**workbench/**: (no front page)" in text
    assert "**music/porch_light/**" in text
    assert "**src/**" not in text  # code belongs on the code map
