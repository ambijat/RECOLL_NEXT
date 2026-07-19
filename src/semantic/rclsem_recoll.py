#!/usr/bin/env python3
"""Lazy adapters from Recoll's authoritative inventory to source documents."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from typing import Any, Callable, Iterator, Optional

from rclsem_segments import SourceDocument


DEFAULT_INVENTORY_QUERY = "mime:*"


class RecollInventoryError(Exception):
    """Raised when the Recoll inventory cannot honor its source contract."""


class RecollBindingUnavailable(RecollInventoryError):
    """Raised when Python cannot import the Recoll extension module."""


def _connect_recoll(confdir: str) -> Any:
    try:
        from recoll import recoll
    except ImportError as ex:
        raise RecollBindingUnavailable(
            "Recoll's Python binding is unavailable in this interpreter. "
            "Run with the Python environment that provides recoll.recoll."
        ) from ex
    return recoll.connect(confdir)


class RecollInventory:
    """Read the complete Recoll inventory without importing Recoll at module load."""

    def __init__(
        self,
        *,
        confdir: str = "",
        query_text: str = DEFAULT_INVENTORY_QUERY,
        connector: Optional[Callable[[str], Any]] = None,
        bridge_python: Optional[os.PathLike[str] | str] = None,
    ):
        if not query_text.strip():
            raise RecollInventoryError("inventory query must be non-empty")
        self.confdir = confdir
        self.query_text = query_text
        self.connector = connector
        self.bridge_python = Path(bridge_python) if bridge_python else None

    def documents(self) -> Iterator[SourceDocument]:
        if self.connector is not None:
            yield from self._binding_documents(self.connector)
            return
        try:
            yield from self._binding_documents(_connect_recoll)
            return
        except RecollBindingUnavailable as binding_error:
            bridge_python = self.bridge_python or discover_recoll_python()
            if bridge_python is None:
                raise RecollBindingUnavailable(
                    f"{binding_error} No bundled Recoll Python runtime was found."
                ) from binding_error
        yield from self._bridge_documents(bridge_python)

    def _binding_documents(
        self, connector: Callable[[str], Any]
    ) -> Iterator[SourceDocument]:
        database = connector(self.confdir)
        query = database.query()
        query.execute(self.query_text, fetchtext=True)
        for result in query:
            document_id = _text_field(result, "rcludi")
            if not document_id:
                raise RecollInventoryError("Recoll result has no stable rcludi")
            yield SourceDocument(
                document_id=document_id,
                text=_text_field(result, "text"),
                title=_text_field(result, "title"),
                path=_text_field(result, "url") or _text_field(result, "filename"),
            )

    def _bridge_documents(self, python_executable: Path) -> Iterator[SourceDocument]:
        if not python_executable.is_file():
            raise RecollBindingUnavailable(
                f"configured Recoll Python runtime does not exist: {python_executable}"
            )
        bridge = Path(__file__).with_name("rclsem_recoll_bridge.py")
        process = subprocess.Popen(
            [
                str(python_executable),
                str(bridge),
                "--confdir",
                self.confdir,
                "--query",
                self.query_text,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert process.stdout is not None
        assert process.stderr is not None
        try:
            for line_number, line in enumerate(process.stdout, start=1):
                yield _decode_bridge_document(line, line_number)
            stderr = process.stderr.read()
            return_code = process.wait()
        finally:
            process.stdout.close()
            process.stderr.close()
            if process.poll() is None:
                process.kill()
                process.wait()
        if return_code != 0:
            detail = _last_nonempty_line(stderr)
            suffix = f": {detail}" if detail else ""
            raise RecollInventoryError(
                f"Recoll inventory bridge exited with code {return_code}{suffix}"
            )


def discover_recoll_python() -> Optional[Path]:
    """Find the matching Python runtime shipped by the Windows Recoll installer."""

    configured = os.environ.get("RECOLL_PYTHON")
    candidates = [Path(configured)] if configured else []
    for variable in ("ProgramFiles", "ProgramFiles(x86)"):
        root = os.environ.get(variable)
        if root:
            candidates.append(
                Path(root) / "Recoll" / "Share" / "filters" / "python" / "python.exe"
            )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _decode_bridge_document(line: str, line_number: int) -> SourceDocument:
    try:
        value = json.loads(line)
    except json.JSONDecodeError as ex:
        raise RecollInventoryError(
            f"Recoll inventory bridge returned invalid JSON at line {line_number}"
        ) from ex
    if not isinstance(value, dict):
        raise RecollInventoryError(
            f"Recoll inventory bridge returned a non-object at line {line_number}"
        )
    expected = {"document_id", "text", "title", "path"}
    if set(value) != expected or not all(isinstance(value[key], str) for key in expected):
        raise RecollInventoryError(
            f"Recoll inventory bridge returned invalid fields at line {line_number}"
        )
    if not value["document_id"]:
        raise RecollInventoryError(
            f"Recoll inventory bridge returned an empty identity at line {line_number}"
        )
    return SourceDocument(**value)


def _last_nonempty_line(value: str) -> str:
    # Recoll diagnostics contain no document body, but keep the surfaced detail
    # bounded so a child process cannot flood the command line.
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    return lines[-1][:300] if lines else ""


def _text_field(result: Any, name: str) -> str:
    value = getattr(result, name, "")
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)
