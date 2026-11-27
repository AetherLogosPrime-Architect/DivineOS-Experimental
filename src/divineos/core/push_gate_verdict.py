"""Did the push gate's suite FAIL, or could the gate not run it at all?

The gate runs the suite in a scratch worktree of the pushed commit. A branch cut
before the gate's own runner module reached main has no such module there, the
runner dies, and the log used to read as "tests failing" about a branch with
nothing wrong. This reads the captured log and says which of the two it was.

Narrow on purpose: only the gate's own runner modules going missing, nothing
collected, or an empty log count as could-not-check. Any FAILED/ERROR line means
the suite really ran, and that is a failure whatever else the log says. Anything
this does not recognise stays a failure, as before. Could-not-check still blocks
the push; it only stops calling the branch red.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass

FAILED = "failed"
COULD_NOT_CHECK = "could_not_check"

# Causes of could-not-check. Only RUNNER_MISSING is cured by a newer main.
RUNNER_MISSING = "runner_missing"
NOTHING_COLLECTED = "nothing_collected"
NO_OUTPUT = "no_output"

EXIT_FAILED = 10
EXIT_COULD_NOT_CHECK = 11

_FAILURE_LINE = re.compile(r"^(FAILED|ERROR)\b", re.MULTILINE)
_RUNNER_MISSING = re.compile(
    r"No module named ['\"]?(divineos\.core\.(?:subprocess_jobs|suite_slot))['\"]?"
)
_NOTHING_COLLECTED = re.compile(r"no tests ran")


@dataclass(frozen=True)
class Verdict:
    kind: str
    reason: str
    cause: str = "none"

    @property
    def exit_code(self) -> int:
        return EXIT_COULD_NOT_CHECK if self.kind == COULD_NOT_CHECK else EXIT_FAILED


def classify(log_text: str) -> Verdict:
    if _FAILURE_LINE.search(log_text):
        return Verdict(FAILED, "the suite ran and reported failures")
    missing = _RUNNER_MISSING.search(log_text)
    if missing:
        return Verdict(
            COULD_NOT_CHECK,
            f"the gate's runner module {missing.group(1)} is not in the pushed commit, "
            "so the suite could not be started there",
            RUNNER_MISSING,
        )
    if _NOTHING_COLLECTED.search(log_text):
        return Verdict(COULD_NOT_CHECK, "no tests ran: nothing was collected", NOTHING_COLLECTED)
    if not log_text.strip():
        return Verdict(COULD_NOT_CHECK, "the run left no output to read", NO_OUTPUT)
    return Verdict(FAILED, "the run ended badly in a way this does not recognise")


def main(argv: list[str]) -> int:
    with open(argv[1], encoding="utf-8", errors="replace") as handle:
        verdict = classify(handle.read())
    print(verdict.kind, verdict.exit_code, verdict.cause, verdict.reason)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
