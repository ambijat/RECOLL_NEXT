#!/usr/bin/env python3
"""Xapian-first lexical, semantic, and fused evidence retrieval."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
import hashlib
import re
from typing import Iterable, Optional, Protocol

from rclsem_events import EventSink
from rclsem_retrieve import EvidenceResult
from rclsem_segments import DeterministicSegmenter, SourceDocument


class HybridRetrievalError(ValueError):
    """Raised when a hybrid retrieval request violates its contract."""


class LexicalDocumentProvider(Protocol):
    def search(self, query_text: str, *, limit: int) -> list[SourceDocument]: ...

    def resolve(self, document_ids: Iterable[str]) -> dict[str, SourceDocument]: ...


class SemanticEvidenceProvider(Protocol):
    def search(self, query: str, *, limit: int = 10) -> list[EvidenceResult]: ...


@dataclass(frozen=True)
class SearchEvidence:
    segment_id: str
    document_id: str
    source_revision: str
    title: str
    path: str
    text: str
    source_start: int
    source_end: int
    similarity: Optional[float]
    retrieval_mode: str
    provenance: tuple[str, ...]
    lexical_rank: Optional[int] = None
    semantic_rank: Optional[int] = None
    fusion_score: Optional[float] = None


@dataclass(frozen=True)
class SearchReport:
    mode: str
    results: tuple[SearchEvidence, ...]
    degraded: bool = False
    semantic_error_type: Optional[str] = None
    stale_rejected: int = 0


class LexicalSearcher:
    """Preserve Recoll rank while projecting documents onto source segments."""

    def __init__(
        self,
        documents: LexicalDocumentProvider,
        *,
        segmenter: Optional[DeterministicSegmenter] = None,
        event_sink: Optional[EventSink] = None,
    ):
        self.documents = documents
        self.segmenter = segmenter or DeterministicSegmenter()
        self.event_sink = event_sink

    def search(self, query: str, *, limit: int) -> list[SearchEvidence]:
        _validate_request(query, limit)
        query_hash = _query_hash(query)
        self._record(
            "search.lexical.started", {"query_sha256": query_hash, "limit": limit}
        )
        try:
            results = []
            for document in self.documents.search(query, limit=limit):
                segment = _best_segment(document, query, self.segmenter)
                if segment is None:
                    continue
                results.append(
                    SearchEvidence(
                        segment_id=segment.segment_id,
                        document_id=document.document_id,
                        source_revision=segment.source_revision,
                        title=document.title,
                        path=document.path,
                        text=segment.text,
                        source_start=segment.source_start,
                        source_end=segment.source_end,
                        similarity=None,
                        retrieval_mode="exact",
                        provenance=("lexical",),
                        lexical_rank=len(results) + 1,
                    )
                )
        except Exception as ex:
            self._record(
                "search.lexical.failed",
                {"query_sha256": query_hash, "error_type": type(ex).__name__},
            )
            raise
        self._record(
            "search.lexical.completed",
            {
                "query_sha256": query_hash,
                "result_count": len(results),
                "document_ids": [item.document_id for item in results],
            },
        )
        return results

    def _record(self, event_type: str, payload: dict[str, object]) -> None:
        if self.event_sink is not None:
            self.event_sink.record(event_type, payload)


class HybridSearchCoordinator:
    """Coordinate authoritative Xapian candidates with optional semantic evidence."""

    MODES = ("exact", "prismatic", "conceptual")

    def __init__(
        self,
        lexical: LexicalSearcher,
        documents: LexicalDocumentProvider,
        semantic: Optional[SemanticEvidenceProvider] = None,
        *,
        candidate_limit: int = 50,
        rrf_k: int = 60,
        lexical_weight: float = 1.0,
        semantic_weight: float = 1.0,
        event_sink: Optional[EventSink] = None,
    ):
        if candidate_limit <= 0 or rrf_k <= 0:
            raise HybridRetrievalError("candidate limit and RRF constant must be positive")
        if lexical_weight <= 0 or semantic_weight <= 0:
            raise HybridRetrievalError("retrieval weights must be positive")
        self.lexical = lexical
        self.documents = documents
        self.semantic = semantic
        self.candidate_limit = candidate_limit
        self.rrf_k = rrf_k
        self.lexical_weight = lexical_weight
        self.semantic_weight = semantic_weight
        self.event_sink = event_sink

    def search(self, query: str, *, mode: str = "prismatic", limit: int = 10) -> SearchReport:
        _validate_request(query, limit)
        if mode not in self.MODES:
            raise HybridRetrievalError(f"unsupported retrieval mode: {mode}")
        if mode != "exact" and self.semantic is None:
            raise HybridRetrievalError(f"{mode} retrieval requires a semantic provider")
        candidate_limit = max(limit, self.candidate_limit)
        if mode == "exact":
            results = self.lexical.search(query, limit=limit)
            return SearchReport(mode=mode, results=tuple(results))

        query_hash = _query_hash(query)
        self._record(
            "search.hybrid.started",
            {
                "query_sha256": query_hash,
                "mode": mode,
                "limit": limit,
                "candidate_limit": candidate_limit,
            },
        )
        try:
            if mode == "conceptual":
                semantic = self.semantic.search(query, limit=candidate_limit)  # type: ignore[union-attr]
                results, stale = self._current_semantic(semantic)
                results = [replace(item, retrieval_mode=mode) for item in results[:limit]]
                report = SearchReport(mode=mode, results=tuple(results), stale_rejected=stale)
            else:
                report = self._prismatic(query, limit, candidate_limit)
        except Exception as ex:
            self._record(
                "search.hybrid.failed",
                {
                    "query_sha256": query_hash,
                    "mode": mode,
                    "error_type": type(ex).__name__,
                },
            )
            raise
        self._record(
            "search.hybrid.completed",
            {
                "query_sha256": query_hash,
                "mode": mode,
                "result_count": len(report.results),
                "document_ids": [item.document_id for item in report.results],
                "degraded": report.degraded,
                "semantic_error_type": report.semantic_error_type,
                "stale_rejected": report.stale_rejected,
            },
        )
        return report

    def _prismatic(self, query: str, limit: int, candidate_limit: int) -> SearchReport:
        with ThreadPoolExecutor(max_workers=2) as executor:
            lexical_future = executor.submit(self.lexical.search, query, limit=candidate_limit)
            semantic_future = executor.submit(
                self.semantic.search, query, limit=candidate_limit  # type: ignore[union-attr]
            )
            lexical = lexical_future.result()
            try:
                semantic = semantic_future.result()
            except Exception as ex:
                return SearchReport(
                    mode="prismatic",
                    results=tuple(
                        replace(item, retrieval_mode="prismatic") for item in lexical[:limit]
                    ),
                    degraded=True,
                    semantic_error_type=type(ex).__name__,
                )
        current_semantic, stale = self._current_semantic(semantic)
        return SearchReport(
            mode="prismatic",
            results=tuple(self._fuse(lexical, current_semantic)[:limit]),
            stale_rejected=stale,
        )

    def _current_semantic(
        self, semantic: list[EvidenceResult]
    ) -> tuple[list[SearchEvidence], int]:
        unique = []
        seen = set()
        for result in semantic:
            if result.document_id not in seen:
                seen.add(result.document_id)
                unique.append(result)
        live = self.documents.resolve(item.document_id for item in unique)
        results = []
        stale = 0
        for rank, result in enumerate(unique, start=1):
            document = live.get(result.document_id)
            if document is None or document.revision() != result.source_revision:
                stale += 1
                continue
            results.append(
                SearchEvidence(
                    segment_id=result.segment_id,
                    document_id=result.document_id,
                    source_revision=result.source_revision,
                    title=document.title,
                    path=document.path,
                    text=result.text,
                    source_start=result.source_start,
                    source_end=result.source_end,
                    similarity=result.similarity,
                    retrieval_mode="conceptual",
                    provenance=("semantic",),
                    semantic_rank=rank,
                )
            )
        return results, stale

    def _fuse(
        self, lexical: list[SearchEvidence], semantic: list[SearchEvidence]
    ) -> list[SearchEvidence]:
        lexical_by_id = {item.document_id: item for item in lexical}
        semantic_by_id = {item.document_id: item for item in semantic}
        document_ids = set(lexical_by_id) | set(semantic_by_id)
        fused = []
        for document_id in document_ids:
            lexical_item = lexical_by_id.get(document_id)
            semantic_item = semantic_by_id.get(document_id)
            score = 0.0
            if lexical_item is not None:
                score += self.lexical_weight / (self.rrf_k + lexical_item.lexical_rank)
            if semantic_item is not None:
                score += self.semantic_weight / (self.rrf_k + semantic_item.semantic_rank)
            evidence = semantic_item or lexical_item
            provenance = tuple(
                name
                for name, item in (("lexical", lexical_item), ("semantic", semantic_item))
                if item is not None
            )
            fused.append(
                replace(
                    evidence,
                    retrieval_mode="prismatic",
                    provenance=provenance,
                    lexical_rank=(lexical_item.lexical_rank if lexical_item else None),
                    semantic_rank=(semantic_item.semantic_rank if semantic_item else None),
                    fusion_score=score,
                )
            )
        fused.sort(
            key=lambda item: (
                -item.fusion_score,
                item.lexical_rank if item.lexical_rank is not None else 10**9,
                item.semantic_rank if item.semantic_rank is not None else 10**9,
                item.document_id,
            )
        )
        return fused

    def _record(self, event_type: str, payload: dict[str, object]) -> None:
        if self.event_sink is not None:
            self.event_sink.record(event_type, payload)


def _best_segment(
    document: SourceDocument, query: str, segmenter: DeterministicSegmenter
):
    segments = segmenter.segment(document)
    if not segments:
        return None
    terms = tuple(dict.fromkeys(re.findall(r"[\w]+", query.casefold())))
    return max(
        segments,
        key=lambda item: (
            sum(item.text.casefold().count(term) for term in terms),
            -item.ordinal,
        ),
    )


def _validate_request(query: str, limit: int) -> None:
    if not isinstance(query, str) or not query.strip():
        raise HybridRetrievalError("query must be a non-empty string")
    if limit <= 0:
        raise HybridRetrievalError("limit must be positive")


def _query_hash(query: str) -> str:
    return hashlib.sha256(query.encode("utf-8")).hexdigest()
