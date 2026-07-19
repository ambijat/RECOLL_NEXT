#!/usr/bin/env python3
"""Deterministic exact semantic retrieval over the local SQLite sidecar."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
from typing import List, Optional, Sequence

from rclsem_events import EventSink
from rclsem_segments import SEGMENTER_VERSION
from rclsem_store import SemanticStore, StoreCompatibilityError, StoredEvidence
from rclsem_sync import EmbeddingProvider


class SemanticRetrievalError(Exception):
    """Raised when a semantic query violates the retrieval contract."""


@dataclass(frozen=True)
class EvidenceResult:
    segment_id: str
    document_id: str
    source_revision: str
    title: str
    path: str
    text: str
    source_start: int
    source_end: int
    similarity: float


class SemanticSearcher:
    """Embed one query and rank stored evidence with exact cosine similarity."""

    def __init__(
        self,
        store: SemanticStore,
        embedding_provider: EmbeddingProvider,
        *,
        embedding_model: str,
        segmenter_version: str = SEGMENTER_VERSION,
        event_sink: Optional[EventSink] = None,
    ):
        if not embedding_model or not segmenter_version:
            raise SemanticRetrievalError("model and segmenter version must be non-empty")
        self.store = store
        self.embedding_provider = embedding_provider
        self.embedding_model = embedding_model
        self.segmenter_version = segmenter_version
        self.event_sink = event_sink

    def search(self, query: str, *, limit: int = 10) -> List[EvidenceResult]:
        if not isinstance(query, str) or not query.strip():
            raise SemanticRetrievalError("query must be a non-empty string")
        if limit <= 0:
            raise SemanticRetrievalError("limit must be positive")
        namespace = self.store.ensure_namespace(
            self.embedding_model, self.segmenter_version
        )
        query_hash = hashlib.sha256(query.encode("utf-8")).hexdigest()
        self._record(
            "search.semantic.started",
            {
                "namespace_id": namespace.namespace_id,
                "embedding_model": self.embedding_model,
                "query_sha256": query_hash,
                "limit": limit,
            },
        )
        try:
            vectors = self.embedding_provider.embed(self.embedding_model, query)
            if len(vectors) != 1:
                raise SemanticRetrievalError(
                    "embedding provider returned the wrong query batch size"
                )
            query_vector = vectors[0]
            if namespace.dimensions is not None and len(query_vector) != namespace.dimensions:
                raise StoreCompatibilityError(
                    f"namespace expects {namespace.dimensions} dimensions, "
                    f"got {len(query_vector)}"
                )
            ranked = [
                (_cosine(query_vector, evidence.embedding), evidence)
                for evidence in self.store.iter_namespace_segments(namespace.namespace_id)
            ]
            ranked.sort(key=lambda item: (-item[0], item[1].segment.segment_id))
            results = [_result(score, evidence) for score, evidence in ranked[:limit]]
        except Exception as ex:
            self._record(
                "search.semantic.failed",
                {
                    "namespace_id": namespace.namespace_id,
                    "query_sha256": query_hash,
                    "error_type": type(ex).__name__,
                },
            )
            raise
        self._record(
            "search.semantic.completed",
            {
                "namespace_id": namespace.namespace_id,
                "query_sha256": query_hash,
                "result_count": len(results),
                "segment_ids": [result.segment_id for result in results],
            },
        )
        return results

    def _record(self, event_type: str, payload: dict[str, object]) -> None:
        if self.event_sink is not None:
            self.event_sink.record(event_type, payload)


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise StoreCompatibilityError("query and stored embedding dimensions differ")
    if not left:
        raise SemanticRetrievalError("query embedding must not be empty")
    if any(not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) for value in left):
        raise SemanticRetrievalError("query embedding contains a non-numeric value")
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0:
        raise SemanticRetrievalError("query embedding must not be a zero vector")
    if right_norm == 0:
        return 0.0
    return sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)


def _result(score: float, evidence: StoredEvidence) -> EvidenceResult:
    segment = evidence.segment
    return EvidenceResult(
        segment_id=segment.segment_id,
        document_id=segment.document_id,
        source_revision=segment.source_revision,
        title=evidence.title,
        path=evidence.path,
        text=segment.text,
        source_start=segment.source_start,
        source_end=segment.source_end,
        similarity=score,
    )
