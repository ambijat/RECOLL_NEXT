#!/usr/bin/env python3
"""Runnable desktop companion for Recoll Next AI perspectives."""

from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Sequence
from urllib.parse import unquote, urlparse


VIEWS = ("answer", "summary", "timeline", "contradictions", "decisions", "actions")
MODES = ("exact", "prismatic", "conceptual")
PROGRESS_PREFIX = "RECOLL_PROGRESS "


class GUIContractError(Exception):
    """Raised when the CLI response cannot be presented safely."""


def build_command(
    script: Path,
    store: Path,
    query_text: str,
    operation: str,
    *,
    view: str = "answer",
    mode: str = "prismatic",
    remember: bool = False,
    evidence_selection: Sequence[tuple[int, str]] = (),
    scope_query: str = "mime:*",
    keep_missing: bool = False,
    sync_timeout: int = 120,
    sync_batch_size: int = 4,
    sync_max_runtime: int = 900,
    confdir: str = "",
    answer_max_runtime: int = 660,
) -> List[str]:
    if operation not in ("search", "ask", "sync"):
        raise GUIContractError("operation must be search, ask, or sync")
    if operation == "sync":
        if not scope_query.strip():
            raise GUIContractError("enter a Recoll scope query first")
        if sync_timeout <= 0 or sync_batch_size <= 0 or sync_max_runtime <= 0:
            raise GUIContractError("timeout, batch size, and runtime limit must be positive")
        command = [
            sys.executable,
            str(script),
            "sync",
            "--store",
            str(store),
            "--json",
            "--query",
            scope_query.strip(),
            "--timeout",
            str(sync_timeout),
            "--batch-size",
            str(sync_batch_size),
            "--max-runtime",
            str(sync_max_runtime),
            "--progress",
        ]
        if confdir.strip():
            command.extend(("--confdir", confdir.strip()))
        if keep_missing:
            command.append("--keep-missing")
        return command
    if not query_text.strip():
        raise GUIContractError("enter a query first")
    command = [sys.executable, str(script), operation]
    if operation == "search":
        if mode not in MODES:
            raise GUIContractError("unsupported retrieval mode")
        if mode != "exact":
            command.extend(("--store", str(store)))
        command.extend(("--json", "--mode", mode, "--timeout", "120", "--limit", "5"))
    else:
        if mode not in MODES:
            raise GUIContractError("unsupported retrieval mode")
        command.extend(("--store", str(store), "--json", "--mode", mode))
        command.append("--progress")
        if view not in VIEWS:
            raise GUIContractError("unsupported perspective")
        if answer_max_runtime <= 0:
            raise GUIContractError("answer runtime limit must be positive")
        if not remember:
            command.append("--no-remember")
        for rank, segment_id in evidence_selection:
            if rank <= 0 or not segment_id:
                raise GUIContractError("selected evidence is incomplete")
            command.extend(("--evidence-rank", str(rank)))
            command.extend(("--expected-segment-id", segment_id))
        command.extend(
            (
                "--timeout",
                "600",
                "--max-runtime",
                str(answer_max_runtime),
                "--evidence-limit",
                str(max(2, len(evidence_selection))),
                "--view",
                view,
            )
        )
    command.append(query_text.strip())
    return command


def parse_progress_line(line: str) -> Optional[Dict[str, Any]]:
    if not line.startswith(PROGRESS_PREFIX):
        return None
    try:
        value = json.loads(line[len(PROGRESS_PREFIX) :])
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) and isinstance(value.get("stage"), str) else None


def clean_title(value: object) -> str:
    title = html.unescape(str(value or "")).strip()
    return re.sub(r"\s+", " ", title)


def provenance_label(item: Dict[str, Any]) -> str:
    values = item.get("provenance") or ()
    if not isinstance(values, (list, tuple)):
        return ""
    return " + ".join(str(value).title() for value in values)


def score_label(item: Dict[str, Any], mode: str) -> str:
    if mode == "exact":
        rank = item.get("lexical_rank")
        return f"Rank #{rank}" if isinstance(rank, int) else ""
    if mode == "conceptual":
        value = item.get("similarity")
        return (
            f"Similarity {float(value):.3f}"
            if isinstance(value, (int, float))
            else ""
        )
    value = item.get("fusion_score")
    if isinstance(value, (int, float)):
        return f"Fusion {float(value):.3f}"
    rank = item.get("lexical_rank")
    return f"Lexical fallback #{rank}" if isinstance(rank, int) else ""


def scope_description(mode: str, store: Path) -> str:
    if mode == "exact":
        return (
            "Scope: active Recoll profile. The semantic store is not used for "
            "Exact retrieval."
        )
    if mode == "conceptual":
        return (
            f"Scope: semantic store {store.name}, with every result revalidated "
            "against the active Recoll profile."
        )
    return (
        f"Scope: active Recoll profile + semantic store {store.name}. "
        "The configured corpora may differ."
    )


def parse_response(raw_output: str) -> Dict[str, Any]:
    try:
        response = json.loads(raw_output)
    except json.JSONDecodeError as ex:
        raise GUIContractError("local AI returned invalid JSON") from ex
    if not isinstance(response, dict):
        raise GUIContractError("local AI response is not an object")
    if response.get("status") == "error":
        raise GUIContractError(str(response.get("error") or "local AI operation failed"))
    if response.get("status") not in ("ready", "answered", "synchronized"):
        raise GUIContractError("local AI returned an unsupported status")
    return response


def local_source_path(source: str) -> Optional[Path]:
    parsed = urlparse(source)
    if parsed.scheme != "file":
        return None
    decoded = unquote(parsed.path)
    if os.name == "nt" and len(decoded) >= 3 and decoded[0] == "/" and decoded[2] == ":":
        decoded = decoded[1:]
    return Path(decoded)


def default_store(repository: Path) -> Path:
    academic = repository / ".local" / "booklibrandom-pdfs.sqlite3"
    return academic if academic.is_file() else repository / ".local" / "semantic.sqlite3"


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store")
    parser.add_argument("--query", default="")
    args = parser.parse_args(argv)

    import tkinter as tk
    from recoll_ai_workspace import AIPerspectiveWorkspace

    repository = Path(__file__).resolve().parents[2]
    store = Path(args.store) if args.store else default_store(repository)
    root = tk.Tk()
    AIPerspectiveWorkspace(root, store=store, query_text=args.query)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
