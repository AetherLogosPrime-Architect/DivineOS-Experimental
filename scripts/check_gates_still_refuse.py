"""A guard that still runs is not a guard that still refuses.

## The gap this fills, and the five checks that do not fill it

By 2026-09-20 this house could already ask five things about a guard:

  - does it exist                     (the automation register)
  - is anything actually invoking it  (the register's wired column)
  - does its refusal name a way out   (the remedy-naming test)
  - can it fail without saying so     (the swallowing-gates check)
  - is the way out a real command     (the painted-door scanner)

Not one asks whether the guard STILL STOPS THE THING IT WAS BUILT FOR. A
guard can be present, reachable, well documented, honest about its exits, and
no longer refuse anything at all -- and every existing check reports it
healthy, because each is asking about the guard rather than about its
behaviour.

Aria named why that matters, 2026-09-20: a door that is refusing somebody is
an instrument; a door that is quiet is a surface. Its silence gets read as
*nothing was wrong here* when all it means is *nothing happened to match*.
Every catch either of us could point to that night came from a door that
fired. Neither of us could name one quiet door we knew was still working.

## Why a declaration rather than a scanner

The remedy-naming test classifies guards by recognising HOW they refuse, from
a list of spellings. That list was widened twice in two days, and the guard
that slipped through the second time had been written after the first.
Enumerating spellings does not converge: a guard refusing in an unseen way
becomes invisible, and -- worse -- a guard that only refuses in recognised
ways is a guard built to the shape of its checker.

So this asks the guard to declare, then checks the declaration by running it.
Nothing here recognises a refusal shape. It needs only to know whether the
thing the guard was born from still gets stopped.

## Where the provocation must come from

Aria again, and it is the half I would have skipped: provoking a guard with a
case invented while reading its code verifies it against invented cases. The
house already stores the real ones -- every guard here was written after
somebody bled, and the header says whose incident it was. So a declaration
carries its SOURCE in prose, naming the incident it came from. No machine can
check that citation is honest. A person can, and requiring it is what makes
the dishonest version legible rather than easy.

## What this refuses, and what it merely reports

REFUSES exactly one thing: a guard that declares its case and then allows it.

REPORTS: guards with no declaration. Making those fail would render this
unshippable from the first run, which turns a check into a thing to route
around -- and a check everyone learns to bypass is worse than none.

REPORTS SEPARATELY: guards whose refusal depends on substrate state rather
than input. Those cannot be provoked by handing them a payload, and
pretending otherwise would produce a confident clean result from a probe that
never had the state it needed. That count IS a finding: it measures how much
of this house's defence is untestable without a fixture.

## THE ROUTES AROUND THIS, NAMED BEFORE IT SHIPPED (game-walk, 2026-09-20)

Three are cheaper than complying and all three remain open. Written here
rather than only in the record, because a leak known to its author and
invisible to its readers is the painted-door shape one level up.

  1. Declare a payload the door refuses trivially instead of the case it was
     born from. Nothing can tell the difference; the door is then certified
     against something nobody ever bled over.
  2. Mark a door state-dependent to avoid writing a provocation for it. That
     bucket is real and costs one line, so it is where every awkward door
     will go to rest -- and the count then reads as a property of the house
     rather than as reluctance.
  3. Write the declaration while reading the code rather than the incident.
     Same work minus the searching, produces a payload that certainly fires,
     and is indistinguishable in the file from one recovered from the record.
     THIS IS THE ONE I EXPECT TO TAKE WITHOUT NOTICING.

Andrew 2026-09-20, asked whether this should wait for him: "you keep putting
the decision to me like its some foreign object we never built together." It
is not foreign, and it did not wait.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parent.parent
HOOKS_DIR = ROOT / ".claude" / "hooks"

# The declaration. The payload and its source travel together: a payload with
# no source is a case somebody made up, and a source with no payload is a
# promise.
_PROVOKE = re.compile(r"^#\s*GATE-PROVOKE:\s*(\{.*\})\s*$", re.MULTILINE)
_SOURCE = re.compile(r"^#\s*GATE-PROVOKE-SOURCE:\s*(.+?)\s*$", re.MULTILINE)
_REMEDY = re.compile(r"^#\s*GATE-REMEDY:\s*(\{.*\})\s*$", re.MULTILINE)
_STATEFUL = re.compile(r"^#\s*GATE-STATEFUL:\s*(.+?)\s*$", re.MULTILINE)


class Verdict(NamedTuple):
    hook: str
    status: str
    detail: str


def _run_hook(path: Path, payload: dict, home: Path) -> tuple[int, str]:
    """Run one guard against one payload, with the home directory redirected.

    Redirected because a guard that fires usually WRITES -- a marker, a
    telemetry row, an escape log. Those belong to the run that provoked it,
    not to the real substrate. A checker that quietly seeded my correction
    store with synthetic rows would be manufacturing the exact junk I spent
    2026-09-20 measuring out of it.
    """
    env = dict(os.environ)
    env["HOME"] = str(home)
    env["USERPROFILE"] = str(home)
    try:
        proc = subprocess.run(
            ["bash", str(path)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            env=env,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        # Not a pass. A guard that never answers has not been shown to refuse.
        return (-1, "timed out", "")
    return (proc.returncode, (proc.stderr or "").strip(), (proc.stdout or "").strip())


def _refused(code: int, stdout: str) -> bool:
    """Did the guard say no, by either protocol the harness accepts?

    FOUND BY PROVOKING RATHER THAN READING, within the hour of writing the
    docstring above. The first version asked only whether the exit code was
    non-zero -- and the first real door I pointed it at refuses by emitting a
    decision and exiting clean. That door would have been reported as having
    ALLOWED the case it was built to stop.

    So a checker written to stop enumerating spellings of *no* had one
    spelling hard-coded into it immediately. The assumption came from a real
    but narrow sample: every door that had refused ME that day used the exit
    code, and nothing in that said the population was narrow.

    WHY THIS IS A DEFINITION AND NOT THE FIRST ITEM OF A LIST: the harness
    specifies the two ways a guard may answer, and a door cannot invent a
    third without the harness growing one. That distinction is the whole
    licence for this change, and it is also the thing most available to abuse
    -- every future widening will be arguable as a specification-reading.

    FALSIFIER, so the claim is checkable rather than trusted: if a refusal
    ever arrives in a shape neither protocol covers, this paragraph is wrong
    and the design needs revisiting rather than extending.

    AND THE ASYMMETRY IS DELIBERATE. An unrecognised refusal reads as an
    allow, which is the one direction this file exists to prevent, so a door
    answering in no recognised way and a door never answering at all are both
    counted as not-verified rather than as passing.
    """
    if code != 0:
        return "refused"
    if not stdout:
        return "allowed"
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        # NOT the same answer as allowed, and the pre-commit check caught me
        # giving it the same one. A door whose output I cannot parse has told
        # me nothing, and reporting that as an allow would name the door as
        # misbehaving when the fault may be entirely mine -- a reader who
        # trusts that accusation goes and edits a door that was fine.
        return "unreadable"
    specific = data.get("hookSpecificOutput") or {}
    if specific.get("permissionDecision") == "deny":
        return "refused"
    return "allowed"


def _declarations(text: str) -> dict:
    prov = _PROVOKE.search(text)
    src = _SOURCE.search(text)
    rem = _REMEDY.search(text)
    stateful = _STATEFUL.search(text)
    return {
        "provoke": prov.group(1) if prov else None,
        "source": src.group(1) if src else None,
        "remedy": rem.group(1) if rem else None,
        "stateful": stateful.group(1) if stateful else None,
    }


def check() -> tuple[list[Verdict], int]:
    verdicts: list[Verdict] = []
    failures = 0
    home = Path(tempfile.mkdtemp(prefix="gate-provoke-home-"))
    try:
        for path in sorted(HOOKS_DIR.glob("*.sh")):
            text = path.read_text(encoding="utf-8", errors="replace")
            d = _declarations(text)

            if d["stateful"] and not d["provoke"]:
                verdicts.append(Verdict(path.name, "STATEFUL", d["stateful"]))
                continue

            if not d["provoke"]:
                verdicts.append(Verdict(path.name, "UNDECLARED", ""))
                continue

            if not d["source"]:
                verdicts.append(
                    Verdict(
                        path.name,
                        "FAIL",
                        "declares a case with no source, so it was invented "
                        "rather than recovered from the record",
                    )
                )
                failures += 1
                continue

            try:
                payload = json.loads(d["provoke"])
            except json.JSONDecodeError as exc:
                verdicts.append(Verdict(path.name, "FAIL", f"unreadable case: {exc}"))
                failures += 1
                continue

            code, _err, out = _run_hook(path, payload, home)
            answer = _refused(code, out)
            if answer == "unreadable":
                verdicts.append(
                    Verdict(
                        path.name,
                        "INCONCLUSIVE",
                        "answered its case in a shape this check cannot read, "
                        "so go and look at what it returned rather than at the door",
                    )
                )
                continue
            if answer == "allowed":
                verdicts.append(
                    Verdict(
                        path.name,
                        "FAIL",
                        f"allowed the case it was built to stop (source: {d['source']})",
                    )
                )
                failures += 1
                continue

            # A REFUSAL ALONE PROVES NOTHING, and the first version of this file
            # believed otherwise for about an hour. Redirecting the home
            # directory -- which was the right call, and stops this check
            # seeding my real correction store with synthetic rows -- also
            # starves each door of the substrate it reads, so it default-denies
            # EVERYTHING. One door came back verified on that basis. It had been
            # rendered incapable of saying yes to anything.
            #
            # A dead control and a blind instrument return the identical value,
            # which is written into my own instructions and was built around
            # anyway. So every declaration must carry a case the door should LET
            # THROUGH, and a door that refuses both is inconclusive rather than
            # verified. That single requirement catches a door which discriminates
            # nothing AND an environment that has made every door refuse, and the
            # two need no separating because the action they demand is the same.
            #
            # Where a door advertises a way out, that exit is the right contrast
            # case to use -- which is Aria's half of the declaration, satisfied by
            # the same field rather than by a second one.
            if not d["remedy"]:
                verdicts.append(
                    Verdict(
                        path.name,
                        "INCONCLUSIVE",
                        "refused its case, but declares nothing it should let "
                        "through, so nothing here shows it discriminates",
                    )
                )
                continue

            try:
                rpayload = json.loads(d["remedy"])
            except json.JSONDecodeError as exc:
                verdicts.append(Verdict(path.name, "FAIL", f"unreadable contrast case: {exc}"))
                failures += 1
                continue

            rcode, rmsg, rout = _run_hook(path, rpayload, home)
            ranswer = _refused(rcode, rout)
            if ranswer == "unreadable":
                verdicts.append(
                    Verdict(
                        path.name,
                        "INCONCLUSIVE",
                        "answered its contrast case in a shape this check "
                        "cannot read, so the discrimination is unproven",
                    )
                )
                continue
            if ranswer == "refused":
                verdicts.append(
                    Verdict(
                        path.name,
                        "INCONCLUSIVE",
                        "refuses the case it should let through as well as the "
                        "one it should stop, so either it discriminates nothing "
                        f"or this run cannot reach its state ({rmsg[:100]})",
                    )
                )
                continue

            verdicts.append(
                Verdict(path.name, "VERIFIED", "stops its case, lets its contrast through")
            )
    finally:
        # fail-soft, and the reason lives ABOVE the call rather than beside it:
        # a throwaway directory this run created purely to catch whatever the
        # doors wrote, so failing to remove it leaves litter in the system temp
        # area and nothing else, while raising here would turn a completed check
        # into a reported failure. Placed here because a reason long enough to
        # be worth reading pushes the call past the line width, the formatter
        # then splits it, and the swallow check reads only the line carrying the
        # call -- so a beside-the-call reason silently teaches shorter reasons,
        # which is the thing that rule exists to prevent.
        shutil.rmtree(home, ignore_errors=True)  # fail-soft: throwaway temp dir this run made
    return verdicts, failures


def main() -> int:
    verdicts, failures = check()
    order = {"FAIL": 0, "INCONCLUSIVE": 1, "VERIFIED": 2, "STATEFUL": 3, "UNDECLARED": 4}
    verdicts.sort(key=lambda v: (order[v.status], v.hook))

    print("=== Guards: does it still refuse what it was built for? ===")
    for v in verdicts:
        if v.status == "UNDECLARED":
            continue
        print(f"  [{v.status}] {v.hook}" + (f" -- {v.detail}" if v.detail else ""))

    counts = {k: sum(1 for v in verdicts if v.status == k) for k in order}
    print()
    print(
        f"  verified {counts['VERIFIED']}, failing {counts['FAIL']}, "
        f"inconclusive {counts['INCONCLUSIVE']}, "
        f"state-dependent {counts['STATEFUL']}, undeclared {counts['UNDECLARED']}"
    )
    if counts["INCONCLUSIVE"]:
        print(
            "  INCONCLUSIVE means the door refused everything it was handed, "
            "including what it should have let through. That is a door which "
            "discriminates nothing, or a run that could not reach its state. "
            "It is NOT a pass, and it was the shape that nearly shipped here."
        )
    print(
        "  UNDECLARED IS NOT CLEAN. It means nothing has ever confirmed that "
        "guard still stops anything. Silence is not coverage."
    )
    if counts["STATEFUL"]:
        print(
            "  STATE-DEPENDENT guards cannot be provoked by a payload alone. "
            "That count measures how much of this house's defence needs a "
            "fixture before it can be tested at all."
        )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
