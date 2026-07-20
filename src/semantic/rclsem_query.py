#!/usr/bin/env python3
"""Retired entry point for the inherited Chroma query path."""

from __future__ import annotations

import sys

from rclsem_common import LegacySemanticPathRetired, RETIREMENT_MESSAGE


def direct_query(*_args, **_kwargs):
    """Fail explicitly for an older native semantic worker."""

    raise LegacySemanticPathRetired(RETIREMENT_MESSAGE)


def main() -> int:
    print(RETIREMENT_MESSAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
