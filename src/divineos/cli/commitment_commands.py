"""Backward-compat shim -- commands moved to entity_commands.py."""


def register(cli):  # noqa: ARG001
    """No-op: commands now registered by entity_commands.register()."""
