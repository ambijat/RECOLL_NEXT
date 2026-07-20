#!/usr/bin/env python3
"""Retired entry point for the inherited Chroma indexer."""

from __future__ import annotations

import sys

from rclsem_common import RETIREMENT_MESSAGE


def main() -> int:
    print(RETIREMENT_MESSAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
