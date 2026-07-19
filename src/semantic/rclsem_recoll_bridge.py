#!/usr/bin/env python3
"""Stream Recoll documents to a parent interpreter as private JSON lines."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confdir", default="")
    parser.add_argument("--query", default="mime:*")
    args = parser.parse_args()

    try:
        from recoll import recoll

        database = recoll.connect(args.confdir)
        query = database.query()
        query.execute(args.query, fetchtext=True)
        for result in query:
            document_id = _text(getattr(result, "rcludi", ""))
            if not document_id:
                raise RuntimeError("Recoll result has no stable rcludi")
            value = {
                "document_id": document_id,
                "text": _text(getattr(result, "text", "")),
                "title": _text(getattr(result, "title", "")),
                "path": _text(getattr(result, "url", ""))
                or _text(getattr(result, "filename", "")),
            }
            sys.stdout.write(
                json.dumps(value, ensure_ascii=True, separators=(",", ":")) + "\n"
            )
    except Exception as ex:
        print(f"{type(ex).__name__}: {ex}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
