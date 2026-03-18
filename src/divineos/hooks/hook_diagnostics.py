"""
Hook Diagnostics Module

Provides tools to diagnose and verify hook configuration and triggering.
Uses HookValidator for consistent validation logic.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List

from divineos.hooks.hook_validator import load_hooks_from_directory

logger = logging.getLogger(__name__)


class HookDiagnostics:
    """Diagnoses hook configuration and triggering issues."""

    def __init__(self, hooks_dir: str = ".kiro/hooks"):
        self.hooks_dir = Path(hooks_dir)
        self.hooks: list[Dict[str, Any]] = []
        self.issues: list[str] = []

    def load_hooks(self) -> List[Dict]:
        """Load all hook files from the hooks directory."""
        valid_hooks, invalid_hooks = load_hooks_from_directory(self.hooks_dir)

        # Track invalid hooks as issues
        for invalid in invalid_hooks:
            self.issues.append(f"Invalid hook {invalid['file']}: {invalid['error']}")

        self.hooks = valid_hooks
        return valid_hooks

    def diagnose_all_hooks(self) -> Dict[str, Any]:
        """Diagnose all hooks and return a comprehensive report."""
        self.load_hooks()

        report: Dict[str, Any] = {
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

        print("\n" + "=" * 60)
        print("HOOK DIAGNOSTICS REPORT")
        print("=" * 60)

        print(f"\nTotal Hooks: {report['total_hooks']}")
        print(f"Valid Hooks: {report['valid_hooks']}")
        print(f"Invalid Hooks: {report['invalid_hooks']}")

        if report["global_issues"]:
            print("\nGlobal Issues:")
            for issue in report["global_issues"]:
                print(f"  ⚠️  {issue}")

        print("\nHook Details:")
        for hook in report["hooks"]:
            status = "✓" if hook["valid"] else "✗"
            print(f"\n  {status} {hook['name']}")
            print(f"     Event: {hook['event_type']}")
            print(f"     Action: {hook['action_type']}")

            if hook["issues"]:
                print("     Issues:")
                for issue in hook["issues"]:
                    print(f"       - {issue}")

        print("\n" + "=" * 60)

        if report["invalid_hooks"] > 0:
            print(f"⚠️  {report['invalid_hooks']} hook(s) need attention!")
        else:
            print("✓ All hooks are valid!")

        print("=" * 60 + "\n")


def run_hook_diagnostics() -> Dict:
    """Run hook diagnostics and return the report."""
    diagnostics = HookDiagnostics()
    report = diagnostics.diagnose_all_hooks()
    diagnostics.print_diagnostic_report()
    return report
