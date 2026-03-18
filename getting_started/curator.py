"""Compatibility alias for curator helpers.

Canonical implementation now lives in ``tradeexecutor.curator.curator``.
Keep this shim so older notebooks importing ``getting_started.curator`` keep
working without local refactors.
"""

from tradeexecutor.curator.curator import *  # noqa: F403

