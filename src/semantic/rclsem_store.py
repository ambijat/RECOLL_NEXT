#!/usr/bin/env python3
"""SQLite storage for versioned semantic document segments and embeddings."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import math
import os
from pathlib import Path
import sqlite3
import struct
from typing import Dict, Iterator, List, Optional, Sequence, Set, Tuple

from rclsem_segments import SourceDocument, TextSegment


STORE_SCHEMA_VERSION = 1


class SemanticStoreError(Exception):
    """Base error raised by semantic storage."""


class StoreCompatibilityError(SemanticStoreError):
    """Raised when vectors conflict with a namespace's immutable contract."""


@dataclass(frozen=True)
class SemanticNamespace:
    namespace_id: str
    embedding_model: str
    segmenter_version: str
    dimensions: Optional[int]


@dataclass(frozen=True)
class StoredSegment:
    segment: TextSegment
    embedding: Tuple[float, ...]


@dataclass(frozen=True)
class StoredEvidence:
    """A stored segment joined with its source-facing document metadata."""

    segment: TextSegment
    title: str
    path: str
    embedding: Tuple[float, ...]


class SemanticStore:
    """Own a rebuildable semantic index without changing the Recoll index."""

    def __init__(self, path: os.PathLike[str] | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def ensure_namespace(
        self, embedding_model: str, segmenter_version: str
    ) -> SemanticNamespace:
        if not embedding_model or not segmenter_version:
            raise SemanticStoreError("model and segmenter version must be non-empty")
        namespace_id = _namespace_id(embedding_model, segmenter_version)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO semantic_namespaces
                    (namespace_id, embedding_model, segmenter_version, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (namespace_id, embedding_model, segmenter_version, _utc_now()),
            )
            row = connection.execute(
                """
                SELECT namespace_id, embedding_model, segmenter_version, dimensions
                FROM semantic_namespaces WHERE namespace_id = ?
                """,
                (namespace_id,),
            ).fetchone()
        if row is None:
            raise SemanticStoreError("could not create semantic namespace")
        return SemanticNamespace(*row)

    def document_revisions(self, namespace_id: str) -> Dict[str, str]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT document_id, source_revision FROM semantic_documents
                WHERE namespace_id = ?
                """,
                (namespace_id,),
            ).fetchall()
        return dict(rows)

    def replace_document(
        self,
        namespace_id: str,
        document: SourceDocument,
        segments: Sequence[TextSegment],
        embeddings: Sequence[Sequence[float]],
    ) -> None:
        if len(segments) != len(embeddings):
            raise SemanticStoreError("segment and embedding counts differ")
        dimensions = _validate_embeddings(embeddings)
        revision = document.revision()
        if any(
            segment.document_id != document.document_id
            or segment.source_revision != revision
            or segment.ordinal != ordinal
            for ordinal, segment in enumerate(segments)
        ):
            raise SemanticStoreError("segments do not belong to the supplied document revision")

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT dimensions FROM semantic_namespaces WHERE namespace_id = ?",
                (namespace_id,),
            ).fetchone()
            if row is None:
                raise SemanticStoreError("semantic namespace does not exist")
            existing_dimensions = row[0]
            if dimensions is not None:
                if existing_dimensions is None:
                    connection.execute(
                        "UPDATE semantic_namespaces SET dimensions = ? WHERE namespace_id = ?",
                        (dimensions, namespace_id),
                    )
                elif existing_dimensions != dimensions:
                    raise StoreCompatibilityError(
                        f"namespace expects {existing_dimensions} dimensions, got {dimensions}"
                    )

            connection.execute(
                "DELETE FROM semantic_documents WHERE namespace_id = ? AND document_id = ?",
                (namespace_id, document.document_id),
            )
            connection.execute(
                """
                INSERT INTO semantic_documents
                    (namespace_id, document_id, source_revision, title, path,
                     segment_count, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    namespace_id,
                    document.document_id,
                    revision,
                    document.title,
                    document.path,
                    len(segments),
                    _utc_now(),
                ),
            )
            connection.executemany(
                """
                INSERT INTO semantic_segments
                    (namespace_id, segment_id, document_id, ordinal, source_start,
                     source_end, text, embedding)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        namespace_id,
                        segment.segment_id,
                        document.document_id,
                        segment.ordinal,
                        segment.source_start,
                        segment.source_end,
                        segment.text,
                        _pack_embedding(embedding),
                    )
                    for segment, embedding in zip(segments, embeddings)
                ],
            )

    def delete_documents_not_in(self, namespace_id: str, active_ids: Set[str]) -> int:
        with self._connect() as connection:
            existing = {
                row[0]
                for row in connection.execute(
                    "SELECT document_id FROM semantic_documents WHERE namespace_id = ?",
                    (namespace_id,),
                )
            }
            stale = sorted(existing - active_ids)
            connection.executemany(
                "DELETE FROM semantic_documents WHERE namespace_id = ? AND document_id = ?",
                [(namespace_id, document_id) for document_id in stale],
            )
        return len(stale)

    def get_namespace(self, namespace_id: str) -> SemanticNamespace:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT namespace_id, embedding_model, segmenter_version, dimensions
                FROM semantic_namespaces WHERE namespace_id = ?
                """,
                (namespace_id,),
            ).fetchone()
        if row is None:
            raise SemanticStoreError("semantic namespace does not exist")
        return SemanticNamespace(*row)

    def read_document_segments(
        self, namespace_id: str, document_id: str
    ) -> List[StoredSegment]:
        namespace = self.get_namespace(namespace_id)
        dimensions = namespace.dimensions or 0
        with self._connect() as connection:
            revision_row = connection.execute(
                """
                SELECT source_revision FROM semantic_documents
                WHERE namespace_id = ? AND document_id = ?
                """,
                (namespace_id, document_id),
            ).fetchone()
            if revision_row is None:
                return []
            rows = connection.execute(
                """
                SELECT segment_id, ordinal, source_start, source_end, text, embedding
                FROM semantic_segments
                WHERE namespace_id = ? AND document_id = ? ORDER BY ordinal
                """,
                (namespace_id, document_id),
            ).fetchall()
        return [
            StoredSegment(
                segment=TextSegment(
                    segment_id=row[0],
                    document_id=document_id,
                    source_revision=revision_row[0],
                    ordinal=row[1],
                    source_start=row[2],
                    source_end=row[3],
                    text=row[4],
                    segmenter_version=namespace.segmenter_version,
                ),
                embedding=_unpack_embedding(row[5], dimensions),
            )
            for row in rows
        ]

    def iter_namespace_segments(self, namespace_id: str) -> Iterator[StoredEvidence]:
        """Yield a stable snapshot of all evidence in one semantic namespace."""

        namespace = self.get_namespace(namespace_id)
        dimensions = namespace.dimensions or 0
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT s.segment_id, s.document_id, d.source_revision, s.ordinal,
                       s.source_start, s.source_end, s.text, d.title, d.path,
                       s.embedding
                FROM semantic_segments AS s
                JOIN semantic_documents AS d
                  ON d.namespace_id = s.namespace_id
                 AND d.document_id = s.document_id
                WHERE s.namespace_id = ?
                ORDER BY s.segment_id
                """,
                (namespace_id,),
            ).fetchall()
        for row in rows:
            yield StoredEvidence(
                segment=TextSegment(
                    segment_id=row[0],
                    document_id=row[1],
                    source_revision=row[2],
                    ordinal=row[3],
                    source_start=row[4],
                    source_end=row[5],
                    text=row[6],
                    segmenter_version=namespace.segmenter_version,
                ),
                title=row[7],
                path=row[8],
                embedding=_unpack_embedding(row[9], dimensions),
            )

    def counts(self, namespace_id: str) -> Tuple[int, int]:
        with self._connect() as connection:
            document_count = connection.execute(
                "SELECT COUNT(*) FROM semantic_documents WHERE namespace_id = ?",
                (namespace_id,),
            ).fetchone()[0]
            segment_count = connection.execute(
                "SELECT COUNT(*) FROM semantic_segments WHERE namespace_id = ?",
                (namespace_id,),
            ).fetchone()[0]
        return document_count, segment_count

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS store_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS semantic_namespaces (
                    namespace_id TEXT PRIMARY KEY,
                    embedding_model TEXT NOT NULL,
                    segmenter_version TEXT NOT NULL,
                    dimensions INTEGER,
                    created_at TEXT NOT NULL,
                    UNIQUE (embedding_model, segmenter_version)
                );
                CREATE TABLE IF NOT EXISTS semantic_documents (
                    namespace_id TEXT NOT NULL,
                    document_id TEXT NOT NULL,
                    source_revision TEXT NOT NULL,
                    title TEXT NOT NULL,
                    path TEXT NOT NULL,
                    segment_count INTEGER NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (namespace_id, document_id),
                    FOREIGN KEY (namespace_id) REFERENCES semantic_namespaces(namespace_id)
                        ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS semantic_segments (
                    namespace_id TEXT NOT NULL,
                    segment_id TEXT NOT NULL,
                    document_id TEXT NOT NULL,
                    ordinal INTEGER NOT NULL,
                    source_start INTEGER NOT NULL,
                    source_end INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    embedding BLOB NOT NULL,
                    PRIMARY KEY (namespace_id, segment_id),
                    UNIQUE (namespace_id, document_id, ordinal),
                    FOREIGN KEY (namespace_id, document_id)
                        REFERENCES semantic_documents(namespace_id, document_id)
                        ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS semantic_segments_document
                    ON semantic_segments(namespace_id, document_id);
                """
            )
            row = connection.execute(
                "SELECT value FROM store_metadata WHERE key = 'schema_version'"
            ).fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO store_metadata(key, value) VALUES ('schema_version', ?)",
                    (str(STORE_SCHEMA_VERSION),),
                )
            elif row[0] != str(STORE_SCHEMA_VERSION):
                raise StoreCompatibilityError(
                    f"store schema {row[0]} is incompatible with {STORE_SCHEMA_VERSION}"
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


def _validate_embeddings(embeddings: Sequence[Sequence[float]]) -> Optional[int]:
    if not embeddings:
        return None
    dimensions = len(embeddings[0])
    if dimensions == 0:
        raise SemanticStoreError("embedding vectors must not be empty")
    for embedding in embeddings:
        if len(embedding) != dimensions:
            raise SemanticStoreError("embedding dimensions are inconsistent")
        if any(
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(value)
            for value in embedding
        ):
            raise SemanticStoreError("embedding contains a non-numeric value")
    return dimensions


def _pack_embedding(embedding: Sequence[float]) -> bytes:
    return struct.pack(f"<{len(embedding)}f", *embedding)


def _unpack_embedding(value: bytes, dimensions: int) -> Tuple[float, ...]:
    if len(value) != dimensions * 4:
        raise StoreCompatibilityError("stored embedding size does not match namespace dimensions")
    return struct.unpack(f"<{dimensions}f", value)


def _namespace_id(embedding_model: str, segmenter_version: str) -> str:
    identity = f"{embedding_model}\0{segmenter_version}".encode("utf-8")
    return hashlib.sha256(identity).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )
