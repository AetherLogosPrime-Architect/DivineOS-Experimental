"""Hook Integration — clarity-system event bus.

# AGENT_RUNTIME — Not wired into CLI pipeline. Provides four hook
# categories (pre_work, post_work, clarity_generated, summary_generated)
# for agents or external code to register callbacks against. No CLI
# command currently calls register_* or trigger_*; this is deliberate —
# the module is reserved for cross-process / agent-driven integration.
#
# Tested via test_clarity_system_verification.py. Dead-architecture
# alarm's scan_wiring() specifically probes this module's
# _clarity_hooks registry; if subscribers ever register here, the
# probe stops firing and the module stops looking dead.
#
# Note: a sibling ViolationHookRegistry previously lived at
# divineos.clarity_enforcement.hooks. That one was removed 2026-04-20
# (zero production callers, pure speculation-abstraction). This module
# keeps the AGENT_RUNTIME marker because the dead-architecture probe
# still watches it — if it stops being probed, reconsider keeping it.

Integrates clarity system with the existing hook infrastructure.
"""

import sqlite3
from collections.abc import Callable
from typing import Any
from uuid import UUID

from loguru import logger

_HI_ERRORS = (ImportError, sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)


class HookIntegrationInterface:
    """Interface for integrating with the hook system."""

    # Registry of clarity hooks
    _clarity_hooks: dict[str, list[Callable[..., Any]]] = {
        "pre_work": [],
        "post_work": [],
        "clarity_generated": [],
        "summary_generated": [],
    }

    @staticmethod
    def register_pre_work_hook(callback: Callable[..., Any]) -> bool:
        """Register a hook to be called before work begins.

        Args:
            callback: Function to call before work

        Returns:
            True if successful

        """
        try:
            HookIntegrationInterface._clarity_hooks["pre_work"].append(callback)
            logger.info(f"Registered pre-work hook: {callback.__name__}")
            return True
        except _HI_ERRORS as e:
            logger.error(f"Error registering pre-work hook: {e}")
            return False

    @staticmethod
    def register_post_work_hook(callback: Callable[..., Any]) -> bool:
        """Register a hook to be called after work completes.

        Args:
            callback: Function to call after work

        Returns:
            True if successful

        """
        try:
            HookIntegrationInterface._clarity_hooks["post_work"].append(callback)
            logger.info(f"Registered post-work hook: {callback.__name__}")
            return True
        except _HI_ERRORS as e:
            logger.error(f"Error registering post-work hook: {e}")
            return False

    @staticmethod
    def register_clarity_generated_hook(callback: Callable[..., Any]) -> bool:
        """Register a hook to be called when clarity statement is generated.

        Args:
            callback: Function to call when clarity is generated

        Returns:
            True if successful

        """
        try:
            HookIntegrationInterface._clarity_hooks["clarity_generated"].append(callback)
            logger.info(f"Registered clarity-generated hook: {callback.__name__}")
            return True
        except _HI_ERRORS as e:
            logger.error(f"Error registering clarity-generated hook: {e}")
            return False

    @staticmethod
    def register_summary_generated_hook(callback: Callable[..., Any]) -> bool:
        """Register a hook to be called when summary is generated.

        Args:
            callback: Function to call when summary is generated

        Returns:
            True if successful

        """
        try:
            HookIntegrationInterface._clarity_hooks["summary_generated"].append(callback)
            logger.info(f"Registered summary-generated hook: {callback.__name__}")
            return True
        except _HI_ERRORS as e:
            logger.error(f"Error registering summary-generated hook: {e}")
            return False

    @staticmethod
    def trigger_pre_work_hooks(session_id: UUID, work_context: dict[str, Any]) -> bool:
        """Trigger all pre-work hooks.

        Args:
            session_id: Current session ID
            work_context: Work context information

        Returns:
            True if all hooks succeeded

        """
        try:
            all_succeeded = True
            for hook in HookIntegrationInterface._clarity_hooks["pre_work"]:
                try:
                    hook(session_id=session_id, work_context=work_context)
                except _HI_ERRORS as e:
                    logger.error(f"Error executing pre-work hook {hook.__name__}: {e}")
                    all_succeeded = False

            logger.info(
                f"Triggered {len(HookIntegrationInterface._clarity_hooks['pre_work'])} pre-work hooks",
            )
            return all_succeeded

        except _HI_ERRORS as e:
            logger.error(f"Error triggering pre-work hooks: {e}")
            return False

    @staticmethod
    def trigger_post_work_hooks(session_id: UUID, summary: Any) -> bool:
        """Trigger all post-work hooks.

        Args:
            session_id: Current session ID
            summary: Post-work summary

        Returns:
            True if all hooks succeeded

        """
        try:
            all_succeeded = True
            for hook in HookIntegrationInterface._clarity_hooks["post_work"]:
                try:
                    hook(session_id=session_id, summary=summary)
                except _HI_ERRORS as e:
                    logger.error(f"Error executing post-work hook {hook.__name__}: {e}")
                    all_succeeded = False

            logger.info(
                f"Triggered {len(HookIntegrationInterface._clarity_hooks['post_work'])} post-work hooks",
            )
            return all_succeeded

        except _HI_ERRORS as e:
            logger.error(f"Error triggering post-work hooks: {e}")
            return False

    @staticmethod
    def trigger_clarity_generated_hooks(session_id: UUID, clarity_statement: Any) -> bool:
        """Trigger all clarity-generated hooks.

        Args:
            session_id: Current session ID
            clarity_statement: Generated clarity statement

        Returns:
            True if all hooks succeeded

        """
        try:
            all_succeeded = True
            for hook in HookIntegrationInterface._clarity_hooks["clarity_generated"]:
                try:
                    hook(session_id=session_id, clarity_statement=clarity_statement)
                except _HI_ERRORS as e:
                    logger.error(f"Error executing clarity-generated hook {hook.__name__}: {e}")
                    all_succeeded = False

            logger.info(
                f"Triggered {len(HookIntegrationInterface._clarity_hooks['clarity_generated'])} clarity-generated hooks",
            )
            return all_succeeded

        except _HI_ERRORS as e:
            logger.error(f"Error triggering clarity-generated hooks: {e}")
            return False

    @staticmethod
    def trigger_summary_generated_hooks(session_id: UUID, summary: Any) -> bool:
        """Trigger all summary-generated hooks.

        Args:
            session_id: Current session ID
            summary: Generated summary

        Returns:
            True if all hooks succeeded

        """
        try:
            all_succeeded = True
            for hook in HookIntegrationInterface._clarity_hooks["summary_generated"]:
                try:
                    hook(session_id=session_id, summary=summary)
                except _HI_ERRORS as e:
                    logger.error(f"Error executing summary-generated hook {hook.__name__}: {e}")
                    all_succeeded = False

            logger.info(
                f"Triggered {len(HookIntegrationInterface._clarity_hooks['summary_generated'])} summary-generated hooks",
            )
            return all_succeeded

        except _HI_ERRORS as e:
            logger.error(f"Error triggering summary-generated hooks: {e}")
            return False

    @staticmethod
    def get_registered_hooks() -> dict[str, int]:
        """Get count of registered hooks by type.

        Returns:
            Dictionary with hook counts

        """
        return {
            hook_type: len(hooks)
            for hook_type, hooks in HookIntegrationInterface._clarity_hooks.items()
        }

    @staticmethod
    def clear_hooks() -> bool:
        """Clear all registered hooks.

        Returns:
            True if successful

        """
        try:
            for hook_type in HookIntegrationInterface._clarity_hooks:
                HookIntegrationInterface._clarity_hooks[hook_type].clear()
            logger.info("Cleared all clarity hooks")
            return True
        except _HI_ERRORS as e:
            logger.error(f"Error clearing hooks: {e}")
            return False
