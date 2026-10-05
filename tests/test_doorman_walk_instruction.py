"""The doorman's walk instruction must match the real `walk apply` command.

2026-09-27: the refusal said `walk apply <id> --lens L`; there is no --lens, and
eight applies copied from the door failed in a row.
"""

import re

from divineos.cli import cli
from divineos.core import work_item_doorman


def _walk_apply():
    return cli.commands["walk"].commands["apply"]


def test_every_flag_the_door_names_for_walk_apply_exists():
    text = work_item_doorman._HOW["council walk"]
    shown = text.split("walk apply", 1)[1].split("`", 1)[0]
    real = {o for p in _walk_apply().params for o in getattr(p, "opts", [])}
    named = set(re.findall(r"--[\w-]+", shown))
    assert named <= real, f"door names {named - real}, not options of walk apply"


def test_the_lens_is_positional_as_the_door_says():
    args = [p.name for p in _walk_apply().params if not getattr(p, "opts", [""])[0].startswith("-")]
    assert args == ["walk_id", "lens"]
