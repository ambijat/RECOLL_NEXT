#!/usr/bin/env python3
"""Store and retrieve cited AI interpretations as secondary local memory."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import struct
from typing import Iterator, Sequence, Tuple


class PerspectiveMemoryError(Exception):
    """Raised when perspective memory cannot satisfy its provenance contract."""


@dataclass(frozen=True)
class PerspectiveCitation:
    segment_id: str
    document_id: str
    source_revision: str


@dataclass(frozen=True)
class PerspectiveResult:
    perspective_id: str
    question: str
    answer: str
    view: str
    chat_model: str
    embedding_model: str
    created_at: str
    citations: Tuple[PerspectiveCitation, ...]
    similarity: float


class PerspectiveMemory:
    """Own a rebuildable, provenance-gated memory inside a semantic sidecar."""

    def __init__(self, path: os.PathLike[str] | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @staticmethod
    def embedding_text(question: str, answer: str, view: str) -> str:
        return f"Perspective: {view}\nQuestion: {question.strip()}\nInterpretation: {answer.strip()}"

    def remember(
        self,
        *,
        question: str,
        answer: str,
        view: str,
        chat_model: str,
        embedding_model: str,
        citations: Sequence[PerspectiveCitation],
        embedding: Sequence[float],
    ) -> str:
        fields = (question, answer, view, chat_model, embedding_model)
        if not all(isinstance(value, str) and value.strip() for value in fields):
            raise PerspectiveMemoryError("perspective fields must be non-empty strings")
        if not citations:
            raise PerspectiveMemoryError("a remembered perspective must cite primary evidence")
        normalized_citations = tuple(citations)
        if any(
            not item.segment_id or not item.document_id or not item.source_revision
            for item in normalized_citations
        ):
            raise PerspectiveMemoryError("perspective citations must retain provenance")
        vector = _validated_vector(embedding)
        citation_json = _citation_json(normalized_citations)
        identity = _perspective_id(
            question, answer, view, chat_model, embedding_model, citation_json
        )
        namespace_id = _namespace_id(embedding_model)
        created_at = _utc_now()

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT dimensions FROM perspective_namespaces WHERE namespace_id = ?",
                (namespace_id,),
            ).fetchone()
            if row is None:
                connection.execute(
                    """
                    INSERT INTO perspective_namespaces
                        (namespace_id, embedding_model, dimensions, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (namespace_id, embedding_model, len(vector), created_at),
                )
            elif row[0] != len(vector):
                raise PerspectiveMemoryError(
                    f"perspective namespace expects {row[0]} dimensions, got {len(vector)}"
                )
            connection.execute(
                """
                INSERT OR IGNORE INTO ai_perspectives
                    (perspective_id, namespace_id, question, answer, view, chat_model,
                     citation_json, created_at, embedding)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    identity,
                    namespace_id,
                    question.strip(),
                    answer.strip(),
                    view.strip(),
                    chat_model.strip(),
                    citation_json,
                    created_at,
                    _pack(vector),
                ),
            )
        return identity

    def search(
        self,
        query_embedding: Sequence[float],
        *,
        embedding_model: str,
        limit: int = 5,
    ) -> list[PerspectiveResult]:
        if limit <= 0:
            raise PerspectiveMemoryError("perspective result limit must be positive")
        vector = _validated_vector(query_embedding)
        namespace_id = _namespace_id(embedding_model)
        with self._connect() as connection:
            namespace = connection.execute(
                "SELECT dimensions FROM perspective_namespaces WHERE namespace_id = ?",
                (namespace_id,),
            ).fetchone()
            if namespace is None:
                return []
            if namespace[0] != len(vector):
                raise PerspectiveMemoryError(
                    f"perspective namespace expects {namespace[0]} dimensions, got {len(vector)}"
                )
            rows = connection.execute(
                """
                SELECT perspective_id, question, answer, view, chat_model,
                       citation_json, created_at, embedding
                FROM ai_perspectives
                WHERE namespace_id = ? ORDER BY perspective_id
                """,
                (namespace_id,),
            ).fetchall()
            ranked = []
            for row in rows:
                citations = _decode_citations(row[5])
                if not _citations_are_current(connection, citations):
                    continue
                ranked.append(
                    PerspectiveResult(
                        perspective_id=row[0],
                        question=row[1],
                        answer=row[2],
                        view=row[3],
                        chat_model=row[4],
                        embedding_model=embedding_model,
                        created_at=row[6],
                        citations=citations,
                        similarity=_cosine(vector, _unpack(row[7], namespace[0])),
                    )
                )
        ranked.sort(key=lambda item: (-item.similarity, item.perspective_id))
        return ranked[:limit]

    def count(self) -> int:
        with self._connect() as connection:
            return connection.execute("SELECT COUNT(*) FROM ai_perspectives").fetchone()[0]

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS perspective_namespaces (
                    namespace_id TEXT PRIMARY KEY,
                    embedding_model TEXT NOT NULL UNIQUE,
                    dimensions INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS ai_perspectives (
                    perspective_id TEXT PRIMARY KEY,
                    namespace_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    view TEXT NOT NULL,
                    chat_model TEXT NOT NULL,
                    citation_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    embedding BLOB NOT NULL,
                    FOREIGN KEY (namespace_id) REFERENCES perspective_namespaces(namespace_id)
                        ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS ai_perspectives_namespace
                    ON ai_perspectives(namespace_id);
                """
            )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()


def _citations_are_current(
    connection: sqlite3.Connection, citations: Sequence[PerspectiveCitation]
) -> bool:
    try:
        for citation in citations:
            row = connection.execute(
                """
                SELECT 1
                FROM semantic_segments AS s
                JOIN semantic_documents AS d
                  ON d.namespace_id = s.namespace_id
                 AND d.document_id = s.document_id
                WHERE s.segment_id = ? AND s.document_id = ?
                  AND d.source_revision = ?
                LIMIT 1
                """,
                (citation.segment_id, citation.document_id, citation.source_revision),
            ).fetchone()
            if row is None:
                return False
    except sqlite3.OperationalError:
        return False
    return True


def _citation_json(citations: Sequence[PerspectiveCitation]) -> str:
    return json.dumps(
        [
            {
                "document_id": item.document_id,
                "segment_id": item.segment_id,
                "source_revision": item.source_revision,
            }
            for item in citations
        ],
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _decode_citations(value: str) -> Tuple[PerspectiveCitation, ...]:
    try:
        items = json.loads(value)
        return tuple(PerspectiveCitation(**item) for item in items)
    except (TypeError, ValueError, json.JSONDecodeError) as ex:
        raise PerspectiveMemoryError("stored perspective citations are invalid") from ex


def _perspective_id(*parts: str) -> str:
    return hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()


def _namespace_id(embedding_model: str) -> str:
    if not embedding_model.strip():
        raise PerspectiveMemoryError("embedding model must be non-empty")
    return hashlib.sha256(("perspective\0" + embedding_model).encode("utf-8")).hexdigest()


def _validated_vector(values: Sequence[float]) -> Tuple[float, ...]:
    try:
        vector = tuple(float(value) for value in values)
    except (TypeError, ValueError) as ex:
        raise PerspectiveMemoryError("perspective embedding must be numeric") from ex
    if not vector or not all(math.isfinite(value) for value in vector):
        raise PerspectiveMemoryError("perspective embedding must be finite and non-empty")
    if not any(value != 0.0 for value in vector):
        raise PerspectiveMemoryError("perspective embedding must not be a zero vector")
    return vector


def _pack(vector: Sequence[float]) -> bytes:
    return struct.pack(f"<{len(vector)}f", *vector)


def _unpack(value: bytes, dimensions: int) -> Tuple[float, ...]:
    if len(value) != dimensions * 4:
        raise PerspectiveMemoryError("stored perspective embedding has invalid dimensions")
    return struct.unpack(f"<{dimensions}f", value)


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        raise PerspectiveMemoryError("cannot rank a zero perspective embedding")
    return numerator / (left_norm * right_norm)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
