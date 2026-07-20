#!/usr/bin/env python3
"""Retirement boundary for the superseded Chroma semantic prototype."""

from __future__ import annotations


RETIREMENT_MESSAGE = (
    "The Chroma semantic prototype has been retired. Use "
    "'python src/semantic/recoll_ai.py sync' and 'search' with a local SQLite store."
)


class LegacySemanticPathRetired(RuntimeError):
    """Raised when an inherited caller reaches the retired Chroma pipeline."""


def retired(*_args, **_kwargs):
    raise LegacySemanticPathRetired(RETIREMENT_MESSAGE)


# Keep bounded failure symbols for an older ENABLE_SEMANTIC binary. They make the
# incompatibility explicit instead of importing an optional package or failing with
# an obscure ImportError. New code must not call these functions.
common_init = retired
get_embedding = retired


def get_rclconfig():
    return None


def deb(message):
    del message
