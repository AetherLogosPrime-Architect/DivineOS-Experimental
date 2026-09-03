"""A freshness check nobody calls is the same as no freshness check.

The automation register rotted 24 automations out of date -- claiming 98 where
the tree had 122, blind to every hook added in weeks, still listing four that no
longer existed. A prior-art search pointed at it would have answered "no such
thing" with the authority of a system-wide index.

AND ITS ALARM HAD EXISTED THE WHOLE TIME. The generator carries a `--check`
mode that exits non-zero on drift. Nothing ever ran it. The register did not
lack a checker; it lacked a CALLER.

That is the disease this whole week has been about, one more time: a built
mechanism sitting dark, reported by nobody, while the thing it guards decays.
Wiring it into pre-commit fixed the rot. These tests exist so the wire cannot
come out again quietly -- because the failure mode is not "someone breaks the
check", it is "the check stops being called and nothing says so".

Found because Aletheia asked, closing her review of the sibling file: "is this
file a function of the repository, or of the machine that last wrote it? The
catalog was the second. I would want to know whether it is the only one."
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PRECOMMIT = ROOT / "scripts" / "precommit.sh"

# (generator, the committed doc it owns). Both are checked for a caller, because
# the catalog's checker was wired and the register's was not, and nothing in the
# tree recorded the difference.
GENERATED_DOCS = [
    ("scripts/generate_automation_register.py", "docs/AUTOMATION_REGISTER.md"),
    ("scripts/generate_capability_catalog.py", "docs/CAPABILITY_CATALOG.md"),
]


def _precommit_text() -> str:
    if not PRECOMMIT.is_file():
        pytest.skip("precommit script not present in this checkout")
    return PRECOMMIT.read_text(encoding="utf-8")


@pytest.mark.parametrize("generator,doc", GENERATED_DOCS)
def test_every_generated_doc_has_something_that_checks_it(generator, doc):
    """Some caller must run a freshness check for each committed generated doc.

    Deliberately loose about HOW. The catalog has a dedicated checker script;
    the register is checked by its own generator's --check mode. Either is fine.
    What is not fine is nobody looking, which is the state the register was in.
    """
    text = _precommit_text()
    gen_name = Path(generator).stem
    doc_name = Path(doc).stem
    referenced = gen_name in text or doc_name.lower() in text.lower()
    assert referenced, (
        f"{doc} is generated and committed, and nothing in pre-commit checks "
        f"whether it still matches the system. That is how it goes stale while "
        f"reading as authoritative -- a stale map is a worse oracle than no map."
    )


@pytest.mark.parametrize("generator,_doc", GENERATED_DOCS)
def test_every_generator_offers_a_check_mode(generator, _doc):
    """--check must exist in the source, or a caller has nothing to call.

    STATIC ON PURPOSE, and the first version was not -- it ran the generators
    for real. That version took down the whole suite: 12,672 errors, because
    the catalog generator probes EVERY command with --help, so one test spawned
    roughly a hundred and eighty processes that hammered the shared databases
    while every other worker was reading them.

    A test written to stop a mechanism going dark, which broke everything by
    insisting on live proof in the wrong room. The live proof belongs in
    pre-commit, where it runs serially on a quiet tree and is the entire point
    of the wiring these tests protect. Here, the wiring is the subject.
    """
    path = ROOT / generator
    if not path.is_file():
        pytest.skip(f"{generator} not present in this checkout")
    source = path.read_text(encoding="utf-8")
    assert '"--check"' in source or "'--check'" in source, (
        f"{generator} has no --check mode, so the caller wired into pre-commit "
        f"has nothing to call. That is a painted door: the wiring looks present "
        f"and checks nothing."
    )
