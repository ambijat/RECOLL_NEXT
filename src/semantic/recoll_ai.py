#!/usr/bin/env python3
"""Command-line entry point for the Recoll Next local AI subsystem."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from typing import Any, Dict, Optional, Sequence

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
    return parser


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
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
