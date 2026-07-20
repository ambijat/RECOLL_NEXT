#!/usr/bin/env python3
"""Command-line entry point for the Recoll Next local AI subsystem."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
from typing import Any, Dict, Optional, Sequence
import uuid

from rclsem_ollama import (
    DEFAULT_ENDPOINT,
    OllamaClient,
    OllamaConnectionError,
    OllamaError,
    OllamaPolicyError,
)


DEFAULT_EMBEDDING_MODEL = "embeddinggemma"
DEFAULT_CHAT_MODEL = "gemma3:4b"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    doctor = subparsers.add_parser("doctor", help="check local Ollama readiness")
    doctor.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    doctor.add_argument("--embedding-model", default=DEFAULT_EMBEDDING_MODEL)
    doctor.add_argument("--chat-model", default=DEFAULT_CHAT_MODEL)
    doctor.add_argument("--timeout", default=3.0, type=float)
    doctor.add_argument("--json", action="store_true", dest="as_json")

    sync = subparsers.add_parser(
        "sync", help="synchronize the authoritative Recoll inventory"
    )
    _add_semantic_options(sync)
    sync.add_argument("--confdir", default="", help="Recoll configuration directory")
    sync.add_argument("--query", default="mime:*", help="Recoll inventory query")
    sync.add_argument(
        "--recoll-python",
        help="Python runtime containing recoll.recoll (auto-detected on Windows)",
    )
    sync.add_argument("--batch-size", default=32, type=int)
    sync.add_argument("--target-chars", default=900, type=int)
    sync.add_argument("--overlap-chars", default=150, type=int)
    sync.add_argument("--keep-missing", action="store_true")

    search = subparsers.add_parser(
        "search", help="retrieve locally indexed evidence by semantic similarity"
    )
    _add_semantic_options(search)
    search.add_argument("query", help="local semantic query")
    search.add_argument("--limit", "-n", default=10, type=int)

    ask = subparsers.add_parser(
        "ask", help="generate a local answer grounded in semantic evidence"
    )
    _add_semantic_options(ask)
    ask.set_defaults(timeout=120.0)
    ask.add_argument("query", help="local question")
    ask.add_argument("--chat-model", default=DEFAULT_CHAT_MODEL)
    ask.add_argument("--evidence-limit", default=6, type=int)
    ask.add_argument(
        "--no-remember",
        action="store_false",
        dest="remember",
        help="do not add this validated answer to local perspective memory",
    )
    ask.set_defaults(remember=True)
    ask.add_argument(
        "--view",
        default="answer",
        choices=(
            "answer",
            "summary",
            "timeline",
            "contradictions",
            "decisions",
            "actions",
        ),
    )

    memory_search = subparsers.add_parser(
        "memory-search", help="retrieve validated prior AI perspectives"
    )
    _add_semantic_options(memory_search)
    memory_search.add_argument("query", help="local perspective-memory query")
    memory_search.add_argument("--limit", "-n", default=5, type=int)
    return parser


def _add_semantic_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--store", required=True, help="semantic SQLite sidecar path")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--embedding-model", default=DEFAULT_EMBEDDING_MODEL)
    parser.add_argument("--timeout", default=30.0, type=float)
    parser.add_argument(
        "--ledger",
        help="event ledger path (default: <store>.events.jsonl)",
    )
    parser.add_argument("--session", dest="session_id")
    parser.add_argument("--json", action="store_true", dest="as_json")


def doctor_report(
    *,
    endpoint: str,
    embedding_model: str,
    chat_model: str,
    timeout: float,
) -> tuple[int, Dict[str, Any]]:
    required_models = [embedding_model, chat_model]
    report: Dict[str, Any] = {
        "status": "unknown",
        "endpoint": endpoint,
        "local_only": True,
        "required_models": required_models,
        "installed_models": [],
        "missing_models": required_models,
    }
    try:
        client = OllamaClient(endpoint, timeout=timeout)
        client.policy.validate_model(embedding_model)
        client.policy.validate_model(chat_model)
        models = client.list_models()
    except OllamaPolicyError as ex:
        report.update(status="policy_error", error=str(ex))
        return 3, report
    except OllamaConnectionError as ex:
        report.update(
            status="unavailable",
            error=str(ex),
            next_action="Install or start Ollama, then rerun this command.",
        )
        return 1, report
    except OllamaError as ex:
        report.update(status="error", error=str(ex))
        return 1, report

    installed_names = {model.name for model in models}
    missing = [
        model for model in required_models if not _model_is_installed(model, installed_names)
    ]
    report["installed_models"] = [asdict(model) for model in models]
    report["missing_models"] = missing
    if missing:
        report.update(
            status="models_missing",
            next_action="Pull missing models: "
            + "; ".join(f"ollama pull {model}" for model in missing),
        )
        return 2, report
    report.update(status="ready", next_action="Ollama is ready for local AI search.")
    return 0, report


def _model_is_installed(required: str, installed: set[str]) -> bool:
    if required in installed:
        return True
    if ":" not in required and required + ":latest" in installed:
        return True
    if required.endswith(":latest") and required[:-7] in installed:
        return True
    return False


def _print_human(report: Dict[str, Any]) -> None:
    print(f"Recoll AI status: {report['status']}")
    print(f"Endpoint: {report['endpoint']}")
    print("Policy: local-only")
    installed = report.get("installed_models") or []
    if installed:
        print("Installed models:")
        for model in installed:
            details = " ".join(
                part for part in (model.get("parameter_size"), model.get("quantization")) if part
            )
            suffix = f" ({details})" if details else ""
            print(f"  - {model['name']}{suffix}")
    missing = report.get("missing_models") or []
    if missing:
        print("Missing required models: " + ", ".join(missing))
    if report.get("error"):
        print("Error: " + report["error"])
    if report.get("next_action"):
        print("Next: " + report["next_action"])


def _event_sink(store_path: str, ledger_path: Optional[str], session_id: Optional[str]):
    from rclsem_events import LedgerEventSink
    from rclsem_ledger import EventLedger

    path = Path(ledger_path) if ledger_path else Path(str(store_path) + ".events.jsonl")
    identity = session_id or "cli-" + uuid.uuid4().hex
    return LedgerEventSink(EventLedger(path), actor="recoll-ai", session_id=identity)


def _run_sync(args: argparse.Namespace) -> Dict[str, Any]:
    from rclsem_recoll import RecollInventory
    from rclsem_segments import DeterministicSegmenter, SegmenterConfig
    from rclsem_store import SemanticStore
    from rclsem_sync import SemanticSynchronizer

    store = SemanticStore(args.store)
    client = OllamaClient(args.endpoint, timeout=args.timeout)
    segmenter = DeterministicSegmenter(
        SegmenterConfig(
            target_chars=args.target_chars,
            overlap_chars=args.overlap_chars,
        )
    )
    synchronizer = SemanticSynchronizer(
        store,
        client,
        embedding_model=args.embedding_model,
        segmenter=segmenter,
        batch_size=args.batch_size,
        event_sink=_event_sink(args.store, args.ledger, args.session_id),
    )
    inventory = RecollInventory(
        confdir=args.confdir,
        query_text=args.query,
        bridge_python=args.recoll_python,
    )
    report = asdict(
        synchronizer.sync(
            inventory.documents(), delete_missing=not args.keep_missing
        )
    )
    return {"status": "synchronized", **report}


def _run_search(args: argparse.Namespace) -> Dict[str, Any]:
    from rclsem_retrieve import SemanticSearcher
    from rclsem_store import SemanticStore

    searcher = SemanticSearcher(
        SemanticStore(args.store),
        OllamaClient(args.endpoint, timeout=args.timeout),
        embedding_model=args.embedding_model,
        event_sink=_event_sink(args.store, args.ledger, args.session_id),
    )
    results = [asdict(result) for result in searcher.search(args.query, limit=args.limit)]
    return {"status": "ready", "result_count": len(results), "results": results}


def _run_ask(args: argparse.Namespace) -> Dict[str, Any]:
    from rclsem_answer import CitedAnswerComposer
    from rclsem_retrieve import SemanticSearcher
    from rclsem_store import SemanticStore

    client = OllamaClient(args.endpoint, timeout=args.timeout)
    sink = _event_sink(args.store, args.ledger, args.session_id)
    searcher = SemanticSearcher(
        SemanticStore(args.store),
        client,
        embedding_model=args.embedding_model,
        event_sink=sink,
    )
    composer = CitedAnswerComposer(
        searcher,
        client,
        chat_model=args.chat_model,
        event_sink=sink,
    )
    cited_answer = composer.ask(
        args.query,
        evidence_limit=args.evidence_limit,
        view=args.view,
    )
    report = {"status": "answered", **asdict(cited_answer), "remembered": False}
    if args.remember and not cited_answer.insufficient_evidence:
        try:
            from rclsem_perspectives import PerspectiveCitation, PerspectiveMemory

            memory = PerspectiveMemory(args.store)
            embedding_text = memory.embedding_text(
                args.query, cited_answer.answer, cited_answer.view
            )
            embeddings = client.embed(args.embedding_model, embedding_text)
            if len(embeddings) != 1:
                raise ValueError("embedding provider returned the wrong perspective batch size")
            perspective_id = memory.remember(
                question=args.query,
                answer=cited_answer.answer,
                view=cited_answer.view,
                chat_model=args.chat_model,
                embedding_model=args.embedding_model,
                citations=[
                    PerspectiveCitation(
                        segment_id=item.segment_id,
                        document_id=item.document_id,
                        source_revision=item.source_revision,
                    )
                    for item in cited_answer.citations
                ],
                embedding=embeddings[0],
            )
            report.update(remembered=True, perspective_id=perspective_id)
            sink.record(
                "perspective.memory.stored",
                {
                    "citation_segment_ids": [
                        item.segment_id for item in cited_answer.citations
                    ],
                    "embedding_model": args.embedding_model,
                    "perspective_id": perspective_id,
                    "view": cited_answer.view,
                },
            )
        except Exception as ex:
            # A secondary-memory failure must never suppress a valid cited answer.
            report["memory_error_type"] = type(ex).__name__
            sink.record(
                "perspective.memory.failed",
                {
                    "embedding_model": args.embedding_model,
                    "error_type": type(ex).__name__,
                    "view": cited_answer.view,
                },
            )
    return report


def _run_memory_search(args: argparse.Namespace) -> Dict[str, Any]:
    from rclsem_perspectives import PerspectiveMemory, PerspectiveSearcher

    client = OllamaClient(args.endpoint, timeout=args.timeout)
    searcher = PerspectiveSearcher(
        PerspectiveMemory(args.store),
        client,
        embedding_model=args.embedding_model,
        event_sink=_event_sink(args.store, args.ledger, args.session_id),
    )
    results = [
        asdict(item)
        for item in searcher.search(args.query, limit=args.limit)
    ]
    return {"status": "memory_ready", "result_count": len(results), "results": results}


def _print_operation(report: Dict[str, Any]) -> None:
    if report["status"] == "synchronized":
        print("Recoll semantic index: synchronized")
        print(f"Namespace: {report['namespace_id']}")
        print(
            "Documents: "
            f"+{report['documents_added']} updated={report['documents_updated']} "
            f"unchanged={report['documents_unchanged']} deleted={report['documents_deleted']}"
        )
        print(f"Segments embedded: {report['segments_embedded']}")
        return
    if report["status"] == "answered":
        print(f"Local AI {report['view']}:")
        print(report["answer"])
        if report["insufficient_evidence"]:
            print("Evidence status: insufficient")
        print("Evidence:")
        if not report["citations"]:
            print("  (none)")
        for position, citation in enumerate(report["citations"], start=1):
            label = citation["title"] or citation["path"] or citation["document_id"]
            print(f"  [{position}] {label}")
            print(
                f"      segment={citation['segment_id']} "
                f"source={citation['path']} "
                f"offsets={citation['source_start']}:{citation['source_end']}"
            )
        if report.get("remembered"):
            print(f"Perspective memory: {report['perspective_id']}")
        elif report.get("memory_error_type"):
            print(f"Perspective memory unavailable: {report['memory_error_type']}")
        return
    if report["status"] == "memory_ready":
        print(f"Perspective memory results: {report['result_count']}")
        for position, result in enumerate(report["results"], start=1):
            print(
                f"{position}. {result['view']} "
                f"(cosine={result['similarity']:.6f})"
            )
            print(f"   Question: {result['question']}")
            print(f"   {result['answer']}")
        return
    print(f"Semantic results: {report['result_count']}")
    for position, result in enumerate(report["results"], start=1):
        label = result["title"] or result["path"] or result["document_id"]
        print(f"{position}. {label} (cosine={result['similarity']:.6f})")
        print(
            f"   source={result['path']} offsets="
            f"{result['source_start']}:{result['source_end']}"
        )
        print(f"   {result['text']}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "doctor":
        code, report = doctor_report(
            endpoint=args.endpoint,
            embedding_model=args.embedding_model,
            chat_model=args.chat_model,
            timeout=args.timeout,
        )
        if args.as_json:
            print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        else:
            _print_human(report)
        return code
    try:
        if args.command == "sync":
            report = _run_sync(args)
        elif args.command == "search":
            report = _run_search(args)
        elif args.command == "ask":
            report = _run_ask(args)
        else:
            report = _run_memory_search(args)
    except Exception as ex:
        # The command line is a trust boundary: report the typed failure, never a
        # traceback which might contain extracted document text.
        error = {"status": "error", "error_type": type(ex).__name__, "error": str(ex)}
        if args.as_json:
            print(json.dumps(error, ensure_ascii=False, sort_keys=True))
        else:
            print(f"Recoll AI error ({error['error_type']}): {error['error']}")
        return 1
    if args.as_json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    else:
        _print_operation(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
