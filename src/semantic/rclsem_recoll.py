#!/usr/bin/env python3
"""Lazy adapter from Recoll's authoritative result inventory to source documents."""

from __future__ import annotations

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
    ):
        if not query_text.strip():
            raise RecollInventoryError("inventory query must be non-empty")
        self.confdir = confdir
        self.query_text = query_text
        self.connector = connector or _connect_recoll

    def documents(self) -> Iterator[SourceDocument]:
        database = self.connector(self.confdir)
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


def _text_field(result: Any, name: str) -> str:
    value = getattr(result, name, "")
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)
