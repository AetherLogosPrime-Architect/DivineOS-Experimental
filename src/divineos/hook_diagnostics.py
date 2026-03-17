"""
Hook Diagnostics Module

Provides tools to diagnose and verify hook configuration and triggering.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


class HookDiagnostics:
    """Diagnoses hook configuration and triggering issues."""
    
    def __init__(self, hooks_dir: str = ".kiro/hooks"):
        self.hooks_dir = Path(hooks_dir)
        self.hooks = []
        self.issues = []
    
    def load_hooks(self) -> List[Dict]:
        """Load all hook files from the hooks directory."""
        if not self.hooks_dir.exists():
            self.issues.append(f"Hooks directory not found: {self.hooks_dir}")
            return []
        
        hooks = []
        for hook_file in self.hooks_dir.glob("*.kiro.hook"):
            try:
                with open(hook_file, 'r') as f:
                    hook_data = json.load(f)
                    hook_data['_file'] = str(hook_file)
                    hooks.append(hook_data)
                    logger.info(f"Loaded hook: {hook_file.name}")
            except json.JSONDecodeError as e:
                self.issues.append(f"Invalid JSON in {hook_file.name}: {e}")
            except Exception as e:
                self.issues.append(f"Error loading {hook_file.name}: {e}")
        
        self.hooks = hooks
        return hooks
    
    def validate_hook_structure(self, hook: Dict) -> List[str]:
        """Validate hook structure and return list of issues."""
        issues = []
        
        # Check required fields
        required_fields = ['name', 'version', 'when', 'then']
        for field in required_fields:
            if field not in hook:
                issues.append(f"Missing required field: {field}")
        
        # Check 'when' structure
        if 'when' in hook:
            when = hook['when']
            if 'type' not in when:
                issues.append("'when' missing 'type' field")
            else:
                valid_types = ['promptSubmit', 'postToolUse', 'agentStop', 'fileEdited', 'fileCreated']
                if when['type'] not in valid_types:
                    issues.append(f"Invalid event type: {when['type']}. Valid types: {valid_types}")
        
        # Check 'then' structure
        if 'then' in hook:
            then = hook['then']
            if 'type' not in then:
                issues.append("'then' missing 'type' field")
            else:
                valid_actions = ['askAgent', 'runCommand']
                if then['type'] not in valid_actions:
                    issues.append(f"Invalid action type: {then['type']}. Valid types: {valid_actions}")
            
            # Check action-specific requirements
            if then.get('type') == 'askAgent' and 'prompt' not in then:
                issues.append("'askAgent' action requires 'prompt' field")
            if then.get('type') == 'runCommand' and 'command' not in then:
                issues.append("'runCommand' action requires 'command' field")
        
        return issues
    
    def diagnose_all_hooks(self) -> Dict:
        """Diagnose all hooks and return a comprehensive report."""
        self.load_hooks()
        
        report = {
            "total_hooks": len(self.hooks),
            "valid_hooks": 0,
            "invalid_hooks": 0,
            "hooks": [],
            "global_issues": self.issues,
        }
        
        for hook in self.hooks:
            hook_issues = self.validate_hook_structure(hook)
            
            hook_report = {
                "name": hook.get('name', 'UNKNOWN'),
                "file": hook.get('_file', 'UNKNOWN'),
                "event_type": hook.get('when', {}).get('type', 'UNKNOWN'),
                "action_type": hook.get('then', {}).get('type', 'UNKNOWN'),
                "valid": len(hook_issues) == 0,
                "issues": hook_issues,
            }
            
            if hook_report["valid"]:
                report["valid_hooks"] += 1
            else:
                report["invalid_hooks"] += 1
            
            report["hooks"].append(hook_report)
        
        return report
    
    def print_diagnostic_report(self) -> None:
        """Print a human-readable diagnostic report."""
        report = self.diagnose_all_hooks()
        
        print("\n" + "="*60)
        print("HOOK DIAGNOSTICS REPORT")
        print("="*60)
        
        print(f"\nTotal Hooks: {report['total_hooks']}")
        print(f"Valid Hooks: {report['valid_hooks']}")
        print(f"Invalid Hooks: {report['invalid_hooks']}")
        
        if report['global_issues']:
            print("\nGlobal Issues:")
            for issue in report['global_issues']:
                print(f"  ⚠️  {issue}")
        
        print("\nHook Details:")
        for hook in report['hooks']:
            status = "✓" if hook['valid'] else "✗"
            print(f"\n  {status} {hook['name']}")
            print(f"     File: {hook['file']}")
            print(f"     Event: {hook['event_type']}")
            print(f"     Action: {hook['action_type']}")
            
            if hook['issues']:
                print(f"     Issues:")
                for issue in hook['issues']:
                    print(f"       - {issue}")
        
        print("\n" + "="*60)
        
        if report['invalid_hooks'] > 0:
            print(f"⚠️  {report['invalid_hooks']} hook(s) need attention!")
        else:
            print("✓ All hooks are valid!")
        
        print("="*60 + "\n")


def run_hook_diagnostics() -> Dict:
    """Run hook diagnostics and return the report."""
    diagnostics = HookDiagnostics()
    report = diagnostics.diagnose_all_hooks()
    diagnostics.print_diagnostic_report()
    return report
