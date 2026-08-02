#!/usr/bin/env python3
"""Incremental document-to-embedding synchronization."""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Callable, Iterable, List, Optional, Protocol, Sequence, Set

from rclsem_events import EventSink
from rclsem_segments import DeterministicSegmenter, SourceDocument
from rclsem_store import SemanticNamespace, SemanticStore


class EmbeddingProvider(Protocol):
    def embed(self, model: str, inputs: str | Sequence[str]) -> List[List[float]]:
        ...


class SynchronizationError(Exception):
    """Raised when a source inventory violates synchronization invariants."""


class SynchronizationTimeout(SynchronizationError):
    """Raised at a safe batch boundary when the total runtime budget expires."""


@dataclass(frozen=True)
class SyncReport:
    namespace_id: str
    documents_added: int
    documents_updated: int
    documents_unchanged: int
    documents_deleted: int
    segments_embedded: int


class SemanticSynchronizer:
    """Synchronize one authoritative document inventory into a semantic namespace."""

    def __init__(
        self,
        store: SemanticStore,
        embedding_provider: EmbeddingProvider,
        *,
        embedding_model: str,
        segmenter: DeterministicSegmenter | None = None,
        batch_size: int = 32,
        event_sink: Optional[EventSink] = None,
        progress_callback: Optional[Callable[[dict[str, object]], None]] = None,
        clock: Callable[[], float] = time.monotonic,
    ):
        if not embedding_model:
            raise SynchronizationError("embedding_model must be non-empty")
        if batch_size <= 0:
            raise SynchronizationError("batch_size must be positive")
        self.store = store
        self.embedding_provider = embedding_provider
        self.embedding_model = embedding_model
        self.segmenter = segmenter or DeterministicSegmenter()
        self.batch_size = batch_size
        self.event_sink = event_sink
        self.progress_callback = progress_callback
        self.clock = clock

    def sync(
        self,
        documents: Iterable[SourceDocument],
        *,
        delete_missing: bool = True,
        max_runtime_seconds: Optional[float] = None,
    ) -> SyncReport:
        if max_runtime_seconds is not None and max_runtime_seconds <= 0:
            raise SynchronizationError("max_runtime_seconds must be positive")
        deadline = (
            self.clock() + max_runtime_seconds
            if max_runtime_seconds is not None
            else None
        )
        namespace = self.store.ensure_namespace(
            self.embedding_model, self.segmenter.version
        )
        self._record(
            "index.semantic.started",
            {
                "namespace_id": namespace.namespace_id,
                "embedding_model": self.embedding_model,
                "segmenter_version": self.segmenter.version,
                "delete_missing": delete_missing,
            },
        )
        self._progress("started", documents_scanned=0, segments_embedded=0)
        try:
            report = self._sync_namespace(
                namespace, documents, delete_missing, deadline=deadline
            )
        except KeyboardInterrupt:
            self._record(
                "index.semantic.cancelled",
                {"namespace_id": namespace.namespace_id},
            )
            self._progress("cancelled")
            raise
        except Exception as ex:
            self._record(
                "index.semantic.failed",
                {
                    "namespace_id": namespace.namespace_id,
                    "error_type": type(ex).__name__,
                },
            )
            raise
        self._record(
            "index.semantic.completed",
            {
                "namespace_id": report.namespace_id,
                "documents_added": report.documents_added,
                "documents_updated": report.documents_updated,
                "documents_unchanged": report.documents_unchanged,
                "documents_deleted": report.documents_deleted,
                "segments_embedded": report.segments_embedded,
            },
        )
        self._progress(
            "completed",
            documents_scanned=(
                report.documents_added
                + report.documents_updated
                + report.documents_unchanged
            ),
            segments_embedded=report.segments_embedded,
        )
        return report

    def _sync_namespace(
        self,
        namespace: SemanticNamespace,
        documents: Iterable[SourceDocument],
        delete_missing: bool,
        *,
        deadline: Optional[float],
    ) -> SyncReport:
        existing = self.store.document_revisions(namespace.namespace_id)
        seen: Set[str] = set()
        added = updated = unchanged = embedded = 0

        for document_index, document in enumerate(documents, start=1):
            self._check_deadline(deadline)
            if document.document_id in seen:
                raise SynchronizationError(
                    f"source inventory contains duplicate document id: {document.document_id}"
                )
            seen.add(document.document_id)
            revision = document.revision()
            if existing.get(document.document_id) == revision:
                unchanged += 1
                self._progress(
                    "document_unchanged",
                    document_index=document_index,
                    documents_scanned=document_index,
                    segments_embedded=embedded,
                )
                continue

            segments = self.segmenter.segment(document)
            embedding_inputs = [
                self.segmenter.embedding_text(document, segment) for segment in segments
            ]
            embeddings: List[List[float]] = []
            batches_total = (
                (len(embedding_inputs) + self.batch_size - 1) // self.batch_size
                if embedding_inputs
                else 0
            )
            self._progress(
                "document_started",
                document_index=document_index,
                documents_scanned=document_index - 1,
                document_segments=len(embedding_inputs),
                batches_total=batches_total,
                segments_embedded=embedded,
            )
            for start in range(0, len(embedding_inputs), self.batch_size):
                self._check_deadline(deadline)
                batch = embedding_inputs[start : start + self.batch_size]
                batch_embeddings = self.embedding_provider.embed(self.embedding_model, batch)
                self._check_deadline(deadline)
                if len(batch_embeddings) != len(batch):
                    raise SynchronizationError("embedding provider returned the wrong batch size")
                embeddings.extend(batch_embeddings)
                batch_index = start // self.batch_size + 1
                self._progress(
                    "batch_completed",
                    document_index=document_index,
                    documents_scanned=document_index - 1,
                    document_segments=len(embedding_inputs),
                    document_segments_completed=len(embeddings),
                    batch_index=batch_index,
                    batches_total=batches_total,
                    segments_embedded=embedded + len(embeddings),
                )

            self.store.replace_document(
                namespace.namespace_id, document, segments, embeddings
            )
            embedded += len(segments)
            if document.document_id in existing:
                updated += 1
            else:
                added += 1
            self._progress(
                "document_completed",
                document_index=document_index,
                documents_scanned=document_index,
                segments_embedded=embedded,
            )

        deleted = 0
        if delete_missing:
            deleted = self.store.delete_documents_not_in(namespace.namespace_id, seen)
        return SyncReport(
            namespace_id=namespace.namespace_id,
            documents_added=added,
            documents_updated=updated,
            documents_unchanged=unchanged,
            documents_deleted=deleted,
            segments_embedded=embedded,
        )

    def _check_deadline(self, deadline: Optional[float]) -> None:
        if deadline is not None and self.clock() >= deadline:
            raise SynchronizationTimeout(
                "semantic synchronization exceeded the configured total runtime; "
                "the in-progress document was not partially installed"
            )

    def _progress(self, stage: str, **payload: object) -> None:
        if self.progress_callback is None:
            return
        try:
            self.progress_callback({"stage": stage, **payload})
        except Exception:
            # Presentation progress must never invalidate a semantic transaction.
            pass

    def _record(self, event_type: str, payload: dict[str, object]) -> None:
        if self.event_sink is not None:
            self.event_sink.record(event_type, payload)
