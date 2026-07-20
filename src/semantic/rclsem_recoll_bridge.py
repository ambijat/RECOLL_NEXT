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
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--resolve", action="store_true")
    parser.add_argument("--skip-missing-identity", action="store_true")
    args = parser.parse_args()

    try:
        from recoll import recoll

        database = recoll.connect(args.confdir)
        if args.resolve:
            for line in sys.stdin:
                document_id = json.loads(line)
                if not isinstance(document_id, str) or not document_id:
                    raise ValueError("resolved document identity must be a string")
                try:
                    result = database.getDoc(document_id)
                except AttributeError:
                    continue
                _write_document(result, skip_missing_identity=True)
        else:
            query = database.query()
            query.execute(args.query, fetchtext=True)
            emitted = 0
            for result in query:
                if not _write_document(
                    result, skip_missing_identity=args.skip_missing_identity
                ):
                    continue
                emitted += 1
                if args.limit and emitted >= args.limit:
                    break
    except Exception as ex:
        print(f"{type(ex).__name__}: {ex}", file=sys.stderr)
        return 1
    return 0


def _write_document(result: Any, *, skip_missing_identity: bool = False) -> bool:
    document_id = _text(getattr(result, "rcludi", ""))
    if not document_id:
        if skip_missing_identity:
            return False
        raise RuntimeError("Recoll result has no stable rcludi")
    value = {
        "document_id": document_id,
        "text": _text(getattr(result, "text", "")),
        "title": _text(getattr(result, "title", "")),
        "path": _text(getattr(result, "url", ""))
        or _text(getattr(result, "filename", "")),
    }
    sys.stdout.write(json.dumps(value, ensure_ascii=True, separators=(",", ":")) + "\n")
    return True


if __name__ == "__main__":
    raise SystemExit(main())
