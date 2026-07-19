#!/usr/bin/env python3
"""Deterministic source-preserving segmentation for semantic indexing."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import List, Optional


SEGMENTER_VERSION = "token-window-v1"
TOKEN_RE = re.compile(r"\S+")
SENTENCE_END_RE = re.compile(r"[.!?][\"')\]]*$")


class SegmentationError(ValueError):
    """Raised when a document or segmenter setting violates the contract."""


@dataclass(frozen=True)
class SourceDocument:
    document_id: str
    text: str
    title: str = ""
    path: str = ""
    source_revision: Optional[str] = None

    def revision(self) -> str:
        if self.source_revision:
            return self.source_revision
        canonical = json.dumps(
            {
                "document_id": self.document_id,
                "path": self.path,
                "text": self.text,
                "title": self.title,
            },
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()


@dataclass(frozen=True)
class TextSegment:
    segment_id: str
    document_id: str
    source_revision: str
    ordinal: int
    source_start: int
    source_end: int
    text: str
    segmenter_version: str = SEGMENTER_VERSION


@dataclass(frozen=True)
class SegmenterConfig:
    target_chars: int = 900
    overlap_chars: int = 150
    boundary_floor_ratio: float = 0.55

    def __post_init__(self) -> None:
        if self.target_chars < 64:
            raise SegmentationError("target_chars must be at least 64")
        if self.overlap_chars < 0 or self.overlap_chars >= self.target_chars:
            raise SegmentationError("overlap_chars must be non-negative and below target_chars")
        if not 0.0 <= self.boundary_floor_ratio <= 1.0:
            raise SegmentationError("boundary_floor_ratio must be between zero and one")


class DeterministicSegmenter:
    """Create overlapping token windows with preferred sentence boundaries."""

    version = SEGMENTER_VERSION

    def __init__(self, config: Optional[SegmenterConfig] = None):
        self.config = config or SegmenterConfig()

    def segment(self, document: SourceDocument) -> List[TextSegment]:
        _validate_document(document)
        tokens = list(TOKEN_RE.finditer(document.text))
        if not tokens:
            return []

        revision = document.revision()
        segments: List[TextSegment] = []
        start_index = 0
        while start_index < len(tokens):
            end_index = self._window_end(tokens, start_index)
            end_index = self._prefer_sentence_boundary(tokens, start_index, end_index)
            source_start = tokens[start_index].start()
            source_end = tokens[end_index - 1].end()
            normalized_text = " ".join(
                token.group(0) for token in tokens[start_index:end_index]
            )
            ordinal = len(segments)
            segment_id = _segment_id(
                document.document_id,
                revision,
                ordinal,
                source_start,
                source_end,
                normalized_text,
            )
            segments.append(
                TextSegment(
                    segment_id=segment_id,
                    document_id=document.document_id,
                    source_revision=revision,
                    ordinal=ordinal,
                    source_start=source_start,
                    source_end=source_end,
                    text=normalized_text,
                )
            )
            if end_index == len(tokens):
                break
            start_index = self._overlap_start(tokens, start_index, end_index)
        return segments

    def embedding_text(self, document: SourceDocument, segment: TextSegment) -> str:
        context = []
        if document.title.strip():
            context.append(document.title.strip())
        if document.path.strip():
            context.append(document.path.strip())
        context.append(segment.text)
        return "\n".join(context)

    def _window_end(self, tokens: list[re.Match[str]], start_index: int) -> int:
        source_start = tokens[start_index].start()
        end_index = start_index + 1
        while end_index < len(tokens):
            candidate_end = tokens[end_index].end()
            if candidate_end - source_start > self.config.target_chars:
                break
            end_index += 1
        return end_index

    def _prefer_sentence_boundary(
        self, tokens: list[re.Match[str]], start_index: int, end_index: int
    ) -> int:
        if end_index == len(tokens):
            return end_index
        source_start = tokens[start_index].start()
        minimum_length = int(self.config.target_chars * self.config.boundary_floor_ratio)
        for candidate in range(end_index, start_index, -1):
            token = tokens[candidate - 1]
            if (
                token.end() - source_start >= minimum_length
                and SENTENCE_END_RE.search(token.group(0))
            ):
                return candidate
        return end_index

    def _overlap_start(
        self, tokens: list[re.Match[str]], start_index: int, end_index: int
    ) -> int:
        if self.config.overlap_chars == 0:
            return end_index
        threshold = tokens[end_index - 1].end() - self.config.overlap_chars
        candidate = end_index - 1
        while candidate > start_index + 1 and tokens[candidate - 1].start() >= threshold:
            candidate -= 1
        return max(start_index + 1, candidate)


def _validate_document(document: SourceDocument) -> None:
    if not isinstance(document.document_id, str) or not document.document_id:
        raise SegmentationError("document_id must be a non-empty string")
    if not isinstance(document.text, str):
        raise SegmentationError("document text must be a string")
    if not isinstance(document.title, str) or not isinstance(document.path, str):
        raise SegmentationError("document title and path must be strings")
    if document.source_revision is not None and (
        not isinstance(document.source_revision, str) or not document.source_revision
    ):
        raise SegmentationError("source_revision must be a non-empty string when supplied")


def _segment_id(
    document_id: str,
    revision: str,
    ordinal: int,
    source_start: int,
    source_end: int,
    text: str,
) -> str:
    identity = "\0".join(
        (
            SEGMENTER_VERSION,
            document_id,
            revision,
            str(ordinal),
            str(source_start),
            str(source_end),
            text,
        )
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()
