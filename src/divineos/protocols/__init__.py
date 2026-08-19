"""Protocols — persistent protocol definitions that survive context compaction.

Restored 2026-08-19. This file was swept up with the delivery-cluster retirement,
and it is not delivery-cluster code — it is the marker that makes this directory
a discovered package. pyproject uses `[tool.setuptools.packages.find]`, which
skips a directory with no `__init__.py`, so removing it would have dropped
`resonant_truth.md` from any non-editable install while every local check
passed, because this checkout is installed editable and reads the source tree.

Second near-loss in this directory in one session: `resonant_truth.md` itself
was deleted earlier tonight in a cleanup commit whose stated rule was to read
everything before deleting it. An 85-byte docstring is not worth the third.
"""
