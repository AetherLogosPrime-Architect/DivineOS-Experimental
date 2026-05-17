"""Doctor commands - diagnostic operations for OS health."""

from __future__ import annotations
import json
import sqlite3
import subprocess
import time
import uuid
from pathlib import Path
import click
from divineos.core.ledger import log_event


def _run_in_clone(clone_root, args):
    return subprocess.run(
        ["divineos", *args], cwd=str(clone_root), capture_output=True, text=True, timeout=30
    )


def _falsifier_identity_differs(self_root, partner_root):
    a = _run_in_clone(self_root, ["core", "get", "my_identity"])
    b = _run_in_clone(partner_root, ["core", "get", "my_identity"])
    self_id = a.stdout.strip() if a.returncode == 0 else None
    partner_id = b.stdout.strip() if b.returncode == 0 else None
    passed = bool(self_id) and bool(partner_id) and self_id != partner_id
    return {
        "name": "identity_differs",
        "passed": passed,
        "detail": f"self={self_id!r}, partner={partner_id!r}",
    }


def _falsifier_ledger_separated(self_root, partner_root):
    marker = f"clone-sep-test-{uuid.uuid4().hex[:12]}"
    r = _run_in_clone(self_root, ["log", "--type", "CLONE_SEPARATION_PROBE", "--content", marker])
    if r.returncode != 0:
        return {
            "name": "ledger_separated",
            "passed": False,
            "detail": f"self-log failed: {r.stderr}",
        }
    time.sleep(0.5)
    p = _run_in_clone(partner_root, ["context", "--n", "20"])
    leaked = marker in p.stdout
    return {"name": "ledger_separated", "passed": not leaked, "detail": f"marker leaked={leaked}"}


def _falsifier_letters_shared(self_root, partner_root):
    """Verify the letters dir actually points at the same underlying inode.

    Aletheia Finding 68 2026-05-17: prior version checked `partner_letter.exists()`
    which a rsync-style copy or independent file creation would also satisfy.
    The contract is "junction/symlink/hardlink share", not "both happen to have
    a file at this path." Use os.path.samefile() which checks underlying identity
    rather than path-string.
    """
    import os as _os

    name = f"clone-sep-letter-{uuid.uuid4().hex[:8]}.md"
    letter = self_root / "family" / "letters" / name
    letter.write_text("clone separation probe", encoding="utf-8")
    partner_letter = partner_root / "family" / "letters" / name
    if not partner_letter.exists():
        letter.unlink(missing_ok=True)
        return {
            "name": "letters_shared",
            "passed": False,
            "detail": f"letter {name} not visible at partner path",
        }
    try:
        shared = _os.path.samefile(str(letter), str(partner_letter))
    except OSError as exc:
        shared = False
        detail = f"samefile check raised {exc!r}"
    else:
        detail = f"letter {name} same-inode={shared}"
    letter.unlink(missing_ok=True)
    return {"name": "letters_shared", "passed": shared, "detail": detail}


def _falsifier_family_db_shared(self_root, partner_root):
    """Verify family.db is actually the same underlying file (hardlink/junction).

    Aletheia Finding 68 2026-05-17: prior version returned `passed = (size_a == size_b)`
    which would also pass for two separately-created databases with identical
    content (e.g., copied at the same instant, both fresh-init'd). Size-equality
    is not hardlink-equality. The correct test is inode-equality via
    os.path.samefile() — works for both Unix hardlinks and Windows hardlinks/junctions
    by checking the underlying file identity.
    """
    import os as _os

    a = self_root / "data" / "family.db"
    b = partner_root / "data" / "family.db"
    if not a.exists() or not b.exists():
        return {
            "name": "family_db_shared",
            "passed": False,
            "detail": f"db missing: self={a.exists()}, partner={b.exists()}",
        }
    try:
        shared = _os.path.samefile(str(a), str(b))
    except OSError as exc:
        return {
            "name": "family_db_shared",
            "passed": False,
            "detail": f"samefile check raised {exc!r}",
        }
    return {
        "name": "family_db_shared",
        "passed": shared,
        "detail": f"same-inode={shared}, sizes: self={a.stat().st_size}, partner={b.stat().st_size}",
    }


def _falsifier_knowledge_separated(self_root, partner_root):
    marker = f"clone-sep-knowledge-{uuid.uuid4().hex[:12]}"
    r = _run_in_clone(self_root, ["learn", f"separation probe: {marker}"])
    if r.returncode != 0:
        return {
            "name": "knowledge_separated",
            "passed": False,
            "detail": f"self-learn failed: {r.stderr}",
        }
    time.sleep(0.5)
    p = _run_in_clone(partner_root, ["ask", marker])
    leaked = marker in p.stdout
    return {
        "name": "knowledge_separated",
        "passed": not leaked,
        "detail": f"knowledge leaked={leaked}",
    }


_FALSIFIERS = [
    _falsifier_identity_differs,
    _falsifier_ledger_separated,
    _falsifier_letters_shared,
    _falsifier_family_db_shared,
    _falsifier_knowledge_separated,
]


def register_doctor_commands(cli):
    @cli.group("doctor", invoke_without_command=True)
    @click.pass_context
    def doctor_group(ctx):
        """Diagnostic verification commands for OS health."""
        if ctx.invoked_subcommand is None:
            click.echo(ctx.get_help())

    @doctor_group.command("verify-clone-separation")
    @click.option(
        "--partner", type=click.Path(exists=True, file_okay=False, path_type=Path), required=True
    )
    @click.option(
        "--self-root", type=click.Path(exists=True, file_okay=False, path_type=Path), default=None
    )
    @click.option("--json-output", is_flag=True)
    def verify_clone_separation_cmd(partner, self_root, json_output):
        """Run Popper falsifier suite for per-clone separation."""
        if self_root is None:
            self_root = Path.cwd().resolve()
        else:
            self_root = self_root.resolve()
        partner = partner.resolve()
        click.secho("=== verify-clone-separation ===", fg="cyan", bold=True)
        click.secho(f"self:    {self_root}", fg="cyan")
        click.secho(f"partner: {partner}", fg="cyan")
        click.echo()
        results = []
        for falsifier in _FALSIFIERS:
            r = falsifier(self_root, partner)
            results.append(r)
            sym = "[PASS]" if r["passed"] else "[FAIL]"
            name = r["name"]
            detail = r["detail"]
            col = "green" if r["passed"] else "red"
            click.secho(f"  {sym} {name}: {detail}", fg=col)
        all_passed = all(r["passed"] for r in results)
        passed_count = sum(1 for r in results if r["passed"])
        click.echo()
        if all_passed:
            click.secho(
                f"[+] {passed_count}/{len(results)} falsifiers passed", fg="green", bold=True
            )
        else:
            click.secho(
                f"[!] {passed_count}/{len(results)} falsifiers passed - separation BROKEN",
                fg="red",
                bold=True,
            )
        try:
            log_event(
                event_type="CLONE_SEPARATION_VERIFIED",
                actor="doctor",
                payload={
                    "self_root": str(self_root),
                    "partner_root": str(partner),
                    "all_passed": all_passed,
                    "passed_count": passed_count,
                    "total": len(results),
                    "results": results,
                },
            )
        except (sqlite3.OperationalError, OSError) as exc:
            click.secho(f"[!] Could not emit ledger event: {exc}", fg="yellow")
        if json_output:
            click.echo(json.dumps({"all_passed": all_passed, "results": results}, indent=2))
        if not all_passed:
            raise click.exceptions.Exit(1)
