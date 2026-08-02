#!/usr/bin/env python3
"""Compose locally generated answers whose citations resolve to retrieved evidence."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import time
from typing import Callable, List, Mapping, Optional, Protocol, Sequence, Tuple

from rclsem_events import EventSink
from rclsem_retrieve import EvidenceResult


ANSWER_VIEWS = ("answer", "summary", "timeline", "contradictions", "decisions", "actions")


class AnswerError(Exception):
    """Base error for local cited-answer composition."""


class AnswerValidationError(AnswerError):
    """Raised when generated output cannot satisfy the evidence contract."""


class AnswerTimeout(AnswerError):
    """Raised at a safe stage boundary when the total answer budget expires."""


class EvidenceRetriever(Protocol):
    def search(self, query: str, *, limit: int = 10) -> List[EvidenceResult]:
        ...


class ChatProvider(Protocol):
    def chat(
        self,
        model: str,
        messages: Sequence[Mapping[str, str]],
        *,
        response_format: Optional[Mapping[str, object] | str] = None,
    ) -> str:
        ...


@dataclass(frozen=True)
class CitedAnswer:
    answer: str
    insufficient_evidence: bool
    view: str
    retrieved_count: int
    citations: Tuple[EvidenceResult, ...]


ANSWER_SCHEMA: Mapping[str, object] = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "insufficient_evidence": {"type": "boolean"},
        "citations": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["answer", "insufficient_evidence", "citations"],
    "additionalProperties": False,
}


class CitedAnswerComposer:
    """Retrieve evidence, ask a local model, and reject invented citations."""

    def __init__(
        self,
        retriever: EvidenceRetriever,
        chat_provider: ChatProvider,
        *,
        chat_model: str,
        event_sink: Optional[EventSink] = None,
        progress_callback: Optional[Callable[[dict[str, object]], None]] = None,
        clock: Callable[[], float] = time.monotonic,
    ):
        if not chat_model:
            raise AnswerError("chat model must be non-empty")
        self.retriever = retriever
        self.chat_provider = chat_provider
        self.chat_model = chat_model
        self.event_sink = event_sink
        self.progress_callback = progress_callback
        self.clock = clock

    def ask(
        self,
        query: str,
        *,
        evidence_limit: int = 6,
        view: str = "answer",
        max_runtime_seconds: Optional[float] = None,
    ) -> CitedAnswer:
        if not isinstance(query, str) or not query.strip():
            raise AnswerError("question must be a non-empty string")
        if evidence_limit <= 0:
            raise AnswerError("evidence_limit must be positive")
        if view not in ANSWER_VIEWS:
            raise AnswerError(f"unsupported answer view: {view}")
        if max_runtime_seconds is not None and max_runtime_seconds <= 0:
            raise AnswerError("max_runtime_seconds must be positive")
        deadline = (
            self.clock() + max_runtime_seconds
            if max_runtime_seconds is not None
            else None
        )

        query_hash = hashlib.sha256(query.encode("utf-8")).hexdigest()
        self._record(
            "answer.local.started",
            {
                "chat_model": self.chat_model,
                "evidence_limit": evidence_limit,
                "query_sha256": query_hash,
                "view": view,
            },
        )
        try:
            self._check_deadline(deadline)
            self._progress("retrieving_evidence")
            evidence = self.retriever.search(query, limit=evidence_limit)
            self._check_deadline(deadline)
            if not evidence:
                result = CitedAnswer(
                    answer=(
                        "No indexed evidence is available for this question. "
                        "Synchronize the semantic index and try again."
                    ),
                    insufficient_evidence=True,
                    view=view,
                    retrieved_count=0,
                    citations=(),
                )
            else:
                self._progress("generating_answer", evidence_count=len(evidence))
                response = self.chat_provider.chat(
                    self.chat_model,
                    _messages(query, view, evidence),
                    response_format=_answer_schema(evidence),
                )
                self._check_deadline(deadline)
                self._progress("validating_citations", evidence_count=len(evidence))
                result = _validated_answer(response, view, evidence)
        except Exception as ex:
            self._record(
                "answer.local.failed",
                {
                    "chat_model": self.chat_model,
                    "error_type": type(ex).__name__,
                    "query_sha256": query_hash,
                    "view": view,
                },
            )
            raise

        self._record(
            "answer.local.completed",
            {
                "chat_model": self.chat_model,
                "citation_segment_ids": [item.segment_id for item in result.citations],
                "insufficient_evidence": result.insufficient_evidence,
                "query_sha256": query_hash,
                "retrieved_count": result.retrieved_count,
                "view": view,
            },
        )
        self._progress(
            "completed",
            evidence_count=result.retrieved_count,
            citation_count=len(result.citations),
        )
        return result

    def _record(self, event_type: str, payload: dict[str, object]) -> None:
        if self.event_sink is not None:
            self.event_sink.record(event_type, payload)

    def _progress(self, stage: str, **payload: object) -> None:
        if self.progress_callback is None:
            return
        try:
            self.progress_callback({"stage": stage, **payload})
        except Exception:
            # Progress is presentation state, never evidence or transaction state.
            pass

    def _check_deadline(self, deadline: Optional[float]) -> None:
        if deadline is not None and self.clock() >= deadline:
            raise AnswerTimeout("local answer exceeded the configured total runtime")


def _messages(
    query: str, view: str, evidence: Sequence[EvidenceResult]
) -> Sequence[Mapping[str, str]]:
    evidence_payload = [
        {
            "segment_id": item.segment_id,
            "document_id": item.document_id,
            "title": item.title,
            "path": item.path,
            "source_start": item.source_start,
            "source_end": item.source_end,
            "text": item.text,
        }
        for item in evidence
    ]
    system = (
        "You are the local evidence analyst for Recoll Next. Use only the supplied "
        "evidence. Do not use outside knowledge. Return JSON matching the schema. "
        "List exact segment_id values for every claim in citations. If the evidence "
        "cannot support an answer, set insufficient_evidence to true and explain the "
        "gap. Never invent a citation."
    )
    user = json.dumps(
        {"question": query, "requested_view": view, "evidence": evidence_payload},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return ({"role": "system", "content": system}, {"role": "user", "content": user})


def _answer_schema(evidence: Sequence[EvidenceResult]) -> Mapping[str, object]:
    """Constrain structured generation to the exact supplied segment identifiers."""
    citation_ids = list(dict.fromkeys(item.segment_id for item in evidence))
    return {
        **ANSWER_SCHEMA,
        "properties": {
            **ANSWER_SCHEMA["properties"],
            "citations": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": citation_ids,
                },
            },
        },
    }


def _validated_answer(
    response: str, view: str, evidence: Sequence[EvidenceResult]
) -> CitedAnswer:
    try:
        value = json.loads(response)
    except json.JSONDecodeError as ex:
        raise AnswerValidationError("local model returned invalid answer JSON") from ex
    if not isinstance(value, dict) or set(value) != {
        "answer",
        "insufficient_evidence",
        "citations",
    }:
        raise AnswerValidationError("local model returned invalid answer fields")
    answer = value["answer"]
    insufficient = value["insufficient_evidence"]
    citation_ids = value["citations"]
    if not isinstance(answer, str) or not answer.strip():
        raise AnswerValidationError("local model returned an empty answer")
    if not isinstance(insufficient, bool):
        raise AnswerValidationError("local model returned an invalid evidence flag")
    if not isinstance(citation_ids, list) or not all(
        isinstance(item, str) for item in citation_ids
    ):
        raise AnswerValidationError("local model returned invalid citations")
    by_id = {item.segment_id: item for item in evidence}
    unknown = sorted(set(citation_ids) - set(by_id))
    if unknown:
        raise AnswerValidationError("local model cited evidence that was not supplied")
    if not insufficient and not citation_ids:
        raise AnswerValidationError("a supported answer must cite at least one segment")
    unique_citations = tuple(dict.fromkeys(citation_ids))
    return CitedAnswer(
        answer=answer.strip(),
        insufficient_evidence=insufficient,
        view=view,
        retrieved_count=len(evidence),
        citations=tuple(by_id[item] for item in unique_citations),
    )
