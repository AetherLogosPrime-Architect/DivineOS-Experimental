"""Hook Diagnostics Module.

Provides tools to diagnose and verify hook configuration and triggering.
Uses HookValidator for consistent validation logic.
"""

from pathlib import Path
from typing import Any

from loguru import logger

from divineos.hooks.hook_validator import load_hooks_from_directory


class HookDiagnostics:
    """Diagnoses hook configuration and triggering issues."""

    def __init__(self, hooks_dir: str = ".kiro/hooks") -> None:
        self.hooks_dir = Path(hooks_dir)
        self.hooks: list[dict[str, Any]] = []
        self.issues: list[str] = []

    def load_hooks(self) -> list[dict[str, Any]]:
        """Load all hook files from the hooks directory."""
        valid_hooks, invalid_hooks = load_hooks_from_directory(self.hooks_dir)

        # Track invalid hooks as issues
        for invalid in invalid_hooks:
            self.issues.append(f"Invalid hook {invalid['file']}: {invalid['error']}")

        self.hooks = valid_hooks
        return valid_hooks

    def diagnose_all_hooks(self) -> dict[str, Any]:
        """Diagnose all hooks and return a comprehensive report."""
        self.load_hooks()

        report: dict[str, Any] = {
            "total_hooks": len(self.hooks),
            "valid_hooks": len(self.hooks),
            "invalid_hooks": len(self.issues),
            "hooks": [],
            "global_issues": self.issues,
        }

        for hook in self.hooks:
            # All hooks loaded here are already validated
            hook_report = {
                "name": hook.get("name", "UNKNOWN"),
                "event_type": hook.get("when", {}).get("type", "UNKNOWN"),
                "action_type": hook.get("then", {}).get("type", "UNKNOWN"),
                "valid": True,
                "issues": [],
            }

            report["hooks"].append(hook_report)

        return report

    def print_diagnostic_report(self) -> None:
        """Print a human-readable diagnostic report."""
        report = self.diagnose_all_hooks()

        logger.debug("\n" + "=" * 60)
        logger.debug("HOOK DIAGNOSTICS REPORT")
        logger.debug("=" * 60)

        logger.debug(f"\nTotal Hooks: {report['total_hooks']}")
        logger.debug(f"Valid Hooks: {report['valid_hooks']}")
        logger.debug(f"Invalid Hooks: {report['invalid_hooks']}")

        if report["global_issues"]:
            logger.debug("\nGlobal Issues:")
            for issue in report["global_issues"]:
                logger.debug(f"  ⚠️  {issue}")

        logger.debug("\nHook Details:")
        for hook in report["hooks"]:
            status = "✓" if hook["valid"] else "✗"
            logger.debug(f"\n  {status} {hook['name']}")
            logger.debug(f"     Event: {hook['event_type']}")
            logger.debug(f"     Action: {hook['action_type']}")

            if hook["issues"]:
                logger.debug("     Issues:")
                for issue in hook["issues"]:
                    logger.debug(f"       - {issue}")

        logger.debug("\n" + "=" * 60)

        if report["invalid_hooks"] > 0:
            logger.debug(f"⚠️  {report['invalid_hooks']} hook(s) need attention!")
        else:
            logger.debug("✓ All hooks are valid!")

        logger.debug("=" * 60 + "\n")


def run_hook_diagnostics() -> dict[str, Any]:
    """Run hook diagnostics and return the report."""
    diagnostics = HookDiagnostics()
    report = diagnostics.diagnose_all_hooks()
    diagnostics.print_diagnostic_report()
    return report
