"""`divineos push <branch>` — foreground push with ledger-event alarms.

Per prereg-a9ecf79d250d. Replaces scripts/push_queued.py with a
proper OS command. Works from any branch's working directory because
divineos is pip-installed editable.
"""

from __future__ import annotations

import json
import sys

import click


def register(cli: click.Group) -> None:
    """Register `divineos push` on the CLI group."""

    @cli.command("push")
    @click.argument("branch")
    @click.option(
        "--force-with-lease",
        is_flag=True,
        default=False,
        help="Pass --force-with-lease to git push (safe force after a rebase).",
    )
    @click.option(
        "--remote",
        default="origin",
        help="Remote name (default: origin).",
    )
    @click.option(
        "--lock-timeout",
        type=int,
        default=7200,
        help="Max seconds to wait on the push-queue lock (default 7200 = 2h).",
    )
    @click.option(
        "--json-out",
        is_flag=True,
        default=False,
        help="Print the result as JSON to stdout (in addition to stderr status).",
    )
    def push_cmd(
        branch: str,
        force_with_lease: bool,
        remote: str,
        lock_timeout: int,
        json_out: bool,
    ) -> None:
        """Push BRANCH to remote, foreground, with file-lock + ledger alarms.

        Concurrent invocations serialize via a single file-lock. Each
        invocation runs foreground with loud stderr status and writes
        PUSH_QUEUED / PUSH_RUNNING / PUSH_DONE / PUSH_FAILED events to
        the ledger so silent-failure becomes structurally impossible.

        Exit code mirrors `git push` (0 on success, non-zero on any
        failure — including the pre-push test gate).
        """
        from divineos.core.push_orchestrator import push_branch

        extra_args: list[str] = []
        if force_with_lease:
            extra_args.append("--force-with-lease")

        result = push_branch(
            branch,
            extra_args=extra_args,
            lock_timeout_seconds=lock_timeout,
            remote=remote,
        )

        if json_out:
            click.echo(
                json.dumps(
                    {
                        "branch": result.branch,
                        "exit_code": result.exit_code,
                        "succeeded": result.succeeded,
                        "stage": result.stage,
                        "note": result.note,
                        "extra_args": result.extra_args,
                    }
                )
            )

        sys.exit(result.exit_code)
