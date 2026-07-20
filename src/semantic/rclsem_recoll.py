#!/usr/bin/env python3
"""Lazy adapters from Recoll's authoritative inventory to source documents."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from typing import Any, Callable, Iterable, Iterator, Optional

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


class RecollQueryService:
    """Run bounded lexical queries and resolve live documents through Recoll."""

    def __init__(
        self,
        *,
        confdir: str = "",
        connector: Optional[Callable[[str], Any]] = None,
        bridge_python: Optional[os.PathLike[str] | str] = None,
    ):
        self.confdir = confdir
        self.connector = connector
        self.bridge_python = Path(bridge_python) if bridge_python else None

    def search(self, query_text: str, *, limit: int) -> list[SourceDocument]:
        if not isinstance(query_text, str) or not query_text.strip():
            raise RecollInventoryError("lexical query must be non-empty")
        if limit <= 0:
            raise RecollInventoryError("lexical result limit must be positive")
        if self.connector is not None:
            return self._binding_search(self.connector, query_text, limit)
        try:
            return self._binding_search(_connect_recoll, query_text, limit)
        except RecollBindingUnavailable as binding_error:
            bridge_python = self.bridge_python or discover_recoll_python()
            if bridge_python is None:
                raise RecollBindingUnavailable(
                    f"{binding_error} No bundled Recoll Python runtime was found."
                ) from binding_error
        return list(self._bridge_search(bridge_python, query_text, limit))

    def resolve(self, document_ids: Iterable[str]) -> dict[str, SourceDocument]:
        identities = tuple(dict.fromkeys(document_ids))
        if any(not isinstance(item, str) or not item for item in identities):
            raise RecollInventoryError("document identities must be non-empty strings")
        if not identities:
            return {}
        if self.connector is not None:
            return self._binding_resolve(self.connector, identities)
        try:
            return self._binding_resolve(_connect_recoll, identities)
        except RecollBindingUnavailable as binding_error:
            bridge_python = self.bridge_python or discover_recoll_python()
            if bridge_python is None:
                raise RecollBindingUnavailable(
                    f"{binding_error} No bundled Recoll Python runtime was found."
                ) from binding_error
        return self._bridge_resolve(bridge_python, identities)

    def _binding_search(
        self, connector: Callable[[str], Any], query_text: str, limit: int
    ) -> list[SourceDocument]:
        database = connector(self.confdir)
        query = database.query()
        query.execute(query_text, fetchtext=True)
        documents = []
        for result in query:
            try:
                documents.append(_source_document(result))
            except RecollInventoryError:
                continue
            if len(documents) >= limit:
                break
        return documents

    def _binding_resolve(
        self, connector: Callable[[str], Any], document_ids: tuple[str, ...]
    ) -> dict[str, SourceDocument]:
        database = connector(self.confdir)
        documents = {}
        for document_id in document_ids:
            try:
                document = _source_document(database.getDoc(document_id))
            except (AttributeError, RecollInventoryError):
                continue
            if document.document_id == document_id:
                documents[document_id] = document
        return documents

    def _bridge_search(
        self, python_executable: Path, query_text: str, limit: int
    ) -> Iterator[SourceDocument]:
        yield from _run_bridge(
            python_executable,
            self.confdir,
            (
                "--query",
                query_text,
                "--limit",
                str(limit),
                "--skip-missing-identity",
            ),
        )

    def _bridge_resolve(
        self, python_executable: Path, document_ids: tuple[str, ...]
    ) -> dict[str, SourceDocument]:
        input_text = "".join(
            json.dumps(item, ensure_ascii=True) + "\n" for item in document_ids
        )
        documents = _run_bridge(
            python_executable,
            self.confdir,
            ("--resolve",),
            input_text=input_text,
        )
        return {item.document_id: item for item in documents}


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


def _run_bridge(
    python_executable: Path,
    confdir: str,
    extra_arguments: tuple[str, ...],
    *,
    input_text: Optional[str] = None,
) -> list[SourceDocument]:
    if not python_executable.is_file():
        raise RecollBindingUnavailable(
            f"configured Recoll Python runtime does not exist: {python_executable}"
        )
    bridge = Path(__file__).with_name("rclsem_recoll_bridge.py")
    process = subprocess.run(
        [
            str(python_executable),
            str(bridge),
            "--confdir",
            confdir,
            *extra_arguments,
        ],
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if process.returncode != 0:
        detail = _last_nonempty_line(process.stderr)
        suffix = f": {detail}" if detail else ""
        raise RecollInventoryError(
            f"Recoll query bridge exited with code {process.returncode}{suffix}"
        )
    return [
        _decode_bridge_document(line, line_number)
        for line_number, line in enumerate(process.stdout.splitlines(), start=1)
        if line.strip()
    ]


def _source_document(result: Any) -> SourceDocument:
    document_id = _text_field(result, "rcludi")
    if not document_id:
        raise RecollInventoryError("Recoll result has no stable rcludi")
    return SourceDocument(
        document_id=document_id,
        text=_text_field(result, "text"),
        title=_text_field(result, "title"),
        path=_text_field(result, "url") or _text_field(result, "filename"),
    )


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
