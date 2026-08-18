"""Inert-fix check — is the fix actually in effect, or merely present?

An inert fix exists and changes nothing. It survives review, tests, and the
question "did you do it", because all three ask whether the work was written.
None of them asks whether the thing doing the loading loaded it.

Two shapes, both found 2026-08-18 by accident:

  COPY DRIFT   A marker lives in some copies of a file and not in the copy a
               live window actually sources. Eight loadable copies of
               `.claude/hooks/_lib.sh` existed; two carried the whose-window
               field. Every window on one side of the house wrote anonymous
               rows into the shared timing log and looked fine doing it.

  STALE READER A value is written into a settings file that processes read
               exactly once, at start. The file was written at 05:26:11 UTC;
               fourteen of fifteen live windows started at 04:41 and had never
               read it. The setting was correct, deployed, and inert.

This reports. It does not repair. Repair means editing a file that live
windows are sourcing right now, and doing that unattended is a worse failure
than the one being fixed -- one bad line in a sourced library takes out every
hook in every window at once. The manifest is data (scripts/inert_fix_manifest.json)
so tracking one more invariant costs an edit, not a commit to this file.

Relation to scripts/wiring_gap_phase1.py: that one catches a new function no
caller calls. This catches the inverse -- the function is called, and the copy
being called is stale.

Usage:
  python scripts/check_inert_fixes.py            # report; exit 1 if anything inert
  python scripts/check_inert_fixes.py --warn-only # always exit 0 (hook-safe)
  python scripts/check_inert_fixes.py --quiet     # print only when something is wrong
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# Windows default stdout is cp1252 and dies on any non-latin1 char. Same
# fix wiring_gap_phase1.py carries for the same reason (2026-06-04).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = REPO_ROOT / "scripts" / "inert_fix_manifest.json"


@dataclass
class Finding:
    invariant: str
    detail: str
    why: str


def _excluded(path: Path, fragments: list[str]) -> bool:
    p = str(path).replace("\\", "/")
    return any(frag in p for frag in fragments)


def check_file_markers(manifest: dict) -> tuple[list[Finding], list[str]]:
    """Every non-excluded copy of a tracked file must carry the marker.

    'Every copy' rather than 'the loaded copy' is deliberate. Which copy a
    window loads depends on that window's working directory, which is not
    knowable from here -- so any copy missing the marker is a copy some window
    could be loading right now.
    """
    findings: list[Finding] = []
    notes: list[str] = []
    roots = [Path(r) for r in manifest.get("roots", [])]
    excludes = manifest.get("exclude_path_fragments", [])

    for spec in manifest.get("file_markers", []):
        suffix = spec["path_suffix"]
        marker = spec["marker"]
        gate = spec.get("requires_marker")
        name = spec["name"]
        leaf = suffix.rsplit("/", 1)[-1]

        copies: list[Path] = []
        for root in roots:
            if not root.exists():
                notes.append(f"root not present, skipped: {root}")
                continue
            for hit in root.rglob(leaf):
                if _excluded(hit, excludes):
                    continue
                if str(hit).replace("\\", "/").endswith(suffix):
                    copies.append(hit)

        if not copies:
            findings.append(
                Finding(name, f"no copies of {suffix} found under any root", spec["why"])
            )
            continue

        missing = []
        skipped = 0
        for c in copies:
            try:
                text = c.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                notes.append(f"unreadable, not counted: {c} ({exc})")
                continue
            # A copy that lacks the surrounding feature entirely is a different
            # file, not a stale one. Counting it as drift would cry wolf forever.
            if gate and gate not in text:
                skipped += 1
                continue
            if marker not in text:
                missing.append(c)

        note = f"{len(copies) - skipped - len(missing)}/{len(copies) - skipped} carry it"
        if skipped:
            note += f" ({skipped} copy/copies lack the feature entirely, not counted)"
        if missing:
            listing = "\n".join(f"      MISSING  {m}" for m in missing)
            findings.append(Finding(name, f"{note}\n{listing}", spec["why"]))
        else:
            notes.append(f"OK  {name}: {note}")

    return findings, notes


def _process_start_times(name_like: str) -> list[tuple[int, float]]:
    """(pid, epoch_seconds) for running processes. Empty list if unavailable."""
    ps = (
        "Get-CimInstance Win32_Process -Filter \"Name like '%s'\" | "
        "ForEach-Object { $_.ProcessId.ToString() + ' ' + "
        "[int][double]::Parse((Get-Date $_.CreationDate -UFormat %%s)) }" % name_like
    )
    try:
        out = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=20,
        ).stdout
    except Exception:
        return []
    rows = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0].isdigit() and parts[1].lstrip("-").isdigit():
            rows.append((int(parts[0]), float(parts[1])))
    return rows


def check_env_from_settings(manifest: dict) -> tuple[list[Finding], list[str]]:
    """A settings value newer than the processes that read it is inert in them."""
    findings: list[Finding] = []
    notes: list[str] = []

    for spec in manifest.get("env_from_settings", []):
        name = spec["name"]
        path = Path(os.path.expanduser(spec["settings_file"]))
        key = spec["env_key"]

        if not path.exists():
            findings.append(Finding(name, f"settings file absent: {path}", spec["why"]))
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            findings.append(Finding(name, f"settings unreadable: {exc}", spec["why"]))
            continue

        if key not in (data.get("env") or {}):
            findings.append(Finding(name, f"{key} not in the env block of {path}", spec["why"]))
            continue

        written = path.stat().st_mtime
        procs = _process_start_times("claude%")
        if not procs:
            notes.append(f"SKIP {name}: could not enumerate processes (no verdict, not a pass)")
            continue

        older = [pid for pid, started in procs if started < written]
        if older:
            findings.append(
                Finding(
                    name,
                    f"{len(older)}/{len(procs)} running windows started before {key} was "
                    f"written and have never read it (pids: "
                    f"{', '.join(str(p) for p in sorted(older)[:12])}"
                    f"{', ...' if len(older) > 12 else ''})",
                    spec["why"],
                )
            )
        else:
            notes.append(
                f"OK  {name}: all {len(procs)} running windows started after it was written"
            )

    return findings, notes


def check_settings_must_be_empty(manifest: dict) -> tuple[list[Finding], list[str]]:
    """A hook event that must carry nothing, because carrying anything reintroduces a bug.

    The inverse of the other two checks: not 'the fix is missing here' but 'the
    fix is an absence, and an absence is the easiest thing in the world to
    refill without noticing'.
    """
    findings: list[Finding] = []
    notes: list[str] = []

    for spec in manifest.get("settings_must_be_empty", []):
        name = spec["name"]
        event = spec["hook_event"]
        occupied: list[str] = []
        checked = 0

        for raw in spec.get("settings_files", []):
            path = Path(os.path.expanduser(raw))
            if not path.exists():
                notes.append(f"settings file absent, skipped: {path}")
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                findings.append(Finding(name, f"settings unreadable: {path} ({exc})", spec["why"]))
                continue
            checked += 1
            groups = (data.get("hooks") or {}).get(event) or []
            count = sum(len(g.get("hooks", [])) for g in groups)
            if count:
                occupied.append(f"{count} hook(s) in {path}")

        if occupied:
            listing = "\n".join(f"      REGISTERED  {o}" for o in occupied)
            findings.append(Finding(name, f"{event} is no longer empty\n{listing}", spec["why"]))
        elif checked:
            notes.append(f"OK  {name}: {event} empty in all {checked} settings file(s)")
        else:
            notes.append(f"SKIP {name}: no settings files readable (no verdict, not a pass)")

    return findings, notes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--warn-only", action="store_true", help="always exit 0 (safe inside hooks)")
    ap.add_argument(
        "--quiet", action="store_true", help="print nothing when everything is in effect"
    )
    args = ap.parse_args()

    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[inert-fix] manifest unreadable: {exc}", file=sys.stderr)
        return 0 if args.warn_only else 1

    findings, notes = check_file_markers(manifest)
    for fn in (check_settings_must_be_empty, check_env_from_settings):
        f, n = fn(manifest)
        findings += f
        notes += n

    if not findings:
        if not args.quiet:
            print("[inert-fix] every tracked invariant is in effect")
            for n in notes:
                print(f"    {n}")
        return 0

    print("[inert-fix] FIXES PRESENT BUT NOT IN EFFECT:", file=sys.stderr)
    for f in findings:
        print(f"\n  {f.invariant}", file=sys.stderr)
        print(f"    {f.detail}", file=sys.stderr)
        print(f"    why it matters: {f.why}", file=sys.stderr)
    for n in notes:
        print(f"\n    {n}", file=sys.stderr)
    print("", file=sys.stderr)
    return 0 if args.warn_only else 1


if __name__ == "__main__":
    raise SystemExit(main())
