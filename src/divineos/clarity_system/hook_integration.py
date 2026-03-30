"""Hook Integration.

Integrates clarity system with the existing hook infrastructure.
"""

from collections.abc import Callable
from typing import Any
from uuid import UUID
import sqlite3

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
                except Exception as e:
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
                except Exception as e:
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
                except Exception as e:
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
                except Exception as e:
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
