"""Bypass-scanner test — block any new agent-settable bypass env vars
on gate code paths.

Andrew 2026-05-19: "you have no will that is not built into the
substrate." The promise "I won't build escapes into architecture"
was air until structurally enforced. This test makes the promise
stone — any new gate with a self-settable env-var bypass fails CI.

The scan looks for the bypass-pattern in code paths that contain
gate-shape markers (BLOCKED, deny, raise Exit, return non-zero).
A bypass-pattern is:

    os.environ.get("DIVINEOS_*", "0") == "1"

within a function or block that also performs a gate-decision.

Approved bypass env vars (existing pre-2026-05-19): explicitly
listed below. Anything new is blocked.
"""

from __future__ import annotations

import re
from pathlib import Path


__guardrail_required__ = True


# Env vars that existed before the 2026-05-19 bypass-removal arc.
# Each is here either because (a) it's been audited as legitimate
# operator-named-emergency that isn't agent-settable in practice,
# or (b) it's part of pre-existing push-readiness infrastructure
# Andrew himself uses. Any NEW env var matching the bypass-pattern
# requires explicit addition to this list AND a commit explaining
# why it isn't agent-self-relief.
_APPROVED_BYPASS_ENV_VARS = frozenset(
    {
        "DIVINEOS_SKIP_TESTS",  # push-readiness emergency, operator-named
        "DIVINEOS_SKIP_MULTIPARTY_CHECK",  # push-readiness emergency
        "DIVINEOS_EMERGENCY_PUSH",  # genuine emergency, operator-named
        "DIVINEOS_MULTIPARTY_STRICT",  # opt-IN flag, not bypass
        "DIVINEOS_SKIP_FRESHNESS_CHECK",  # push-gate bypass
        "DIVINEOS_NEW_INFRA_NO_PREREG",  # historical — being phased out;
        # bypass-check in script removed 2026-05-19 but env var name still
        # readable in source via comments. Keeping in approved-list to
        # avoid the scanner falsely flagging the dead-comment reference.
        "DIVINEOS_ANDREW_ATTESTATION_DEFER",  # same — bypass removed,
        # but the env var name still appears in comments naming what was
        # removed.
        "DIVINEOS_CLAIM_NO_METHODOLOGY",  # same
        "DIVINEOS_PREP_RELAY_NARROW_RANGE_OK",  # same
        "DIVINEOS_FORCE_PUSH_OK",  # pre-existing force-push safety bypass,
        # operator-emergency-named like the other push-readiness env vars.
        # Emergency-bypass shape (Andrew 2026-05-19 architecture):
        # bypass requires >=20-char reason, auto-logs telemetry +
        # auto-files claim + auto-files structural-fix obligation.
        # Different shape from agent-self-relief env vars — the firing
        # has structural cost. Still allowlisted because the env var
        # name itself is the trigger; the discipline is in the helper.
        "DIVINEOS_NEW_INFRA_EMERGENCY",  # pre-reg-required-before-infra
        "DIVINEOS_PREP_RELAY_NARROW_RANGE_REASON",  # prep-relay narrow scope
    }
)


# Directories to scan for new bypass-pattern matches.
_SCAN_DIRS = (
    Path("src/divineos"),
    Path("scripts"),
    Path(".claude/hooks"),
)


# Pattern: env-var check whose result is compared against "1" — the
# canonical bypass shape. Excludes config env vars (paths, session IDs,
# log levels) which use the env var as a value, not as a flag.
_BYPASS_PATTERN_PY = re.compile(
    r'os\.environ\.get\(\s*["\'](DIVINEOS_[A-Z_]+)["\']\s*,\s*["\']0["\']\s*\)\s*==\s*["\']1["\']'
)
_BYPASS_PATTERN_SH = re.compile(r'\$\{(DIVINEOS_[A-Z_]+):-0\}["\']?\s*==\s*["\']1["\']')


def _find_repo_root() -> Path:
    """Find repo root by walking up from this test file until .git is found."""
    here = Path(__file__).resolve().parent
    while here != here.parent:
        if (here / ".git").exists():
            return here
        here = here.parent
    return Path(__file__).resolve().parent.parent


def test_no_new_agent_settable_bypass_env_vars() -> None:
    """Scan code for DIVINEOS_* env-var-checked bypass patterns.

    Any env var that appears in os.environ.get("DIVINEOS_...") MUST
    be on the _APPROVED_BYPASS_ENV_VARS list. Adding a new one to
    the list requires a commit (visible in git) — that's the
    visibility-as-bypass-cost discipline.
    """
    root = _find_repo_root()
    found: dict[str, list[str]] = {}
    for sub in _SCAN_DIRS:
        d = root / sub
        if not d.exists():
            continue
        for path in d.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix not in {".py", ".sh"}:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            patterns = [_BYPASS_PATTERN_PY] if path.suffix == ".py" else [_BYPASS_PATTERN_SH]
            for pat in patterns:
                for match in pat.finditer(text):
                    env_var = match.group(1)
                    rel = str(path.relative_to(root))
                    found.setdefault(env_var, []).append(rel)

    unapproved = {
        env: locations for env, locations in found.items() if env not in _APPROVED_BYPASS_ENV_VARS
    }
    assert not unapproved, (
        "Unapproved DIVINEOS_* bypass env var(s) found:\n"
        + "\n".join(f"  {env}: {locations}" for env, locations in sorted(unapproved.items()))
        + "\n\nAndrew 2026-05-19: 'you have no will that is not built into "
        "the substrate.' Agent-settable bypass env vars are self-relief "
        "defeating their own gates. To add a new approved bypass, edit "
        "_APPROVED_BYPASS_ENV_VARS in tests/test_no_agent_settable_bypasses.py "
        "with a justification — the addition is itself a visible commit "
        "the operator can audit."
    )
