import json
from pathlib import Path
import sys
import unittest


SEMANTIC_SOURCE = Path(__file__).resolve().parents[2] / "src" / "semantic"
sys.path.insert(0, str(SEMANTIC_SOURCE))

from recoll_ai import _build_parser  # noqa: E402
from rclsem_answer import (  # noqa: E402
    ANSWER_SCHEMA,
    AnswerValidationError,
    CitedAnswerComposer,
)
from rclsem_retrieve import EvidenceResult  # noqa: E402


def evidence(segment_id="segment-1"):
    return EvidenceResult(
        segment_id=segment_id,
        document_id="document-1",
        source_revision="revision-1",
        title="Architecture decision",
        path="docs/ARCHITECTURE.md",
        text="Ollama remains local and the endpoint is configurable.",
        source_start=10,
        source_end=65,
        similarity=0.91,
    )


class FakeRetriever:
    def __init__(self, results):
        self.results = results
        self.calls = []

    def search(self, query, *, limit=10):
        self.calls.append((query, limit))
        return list(self.results)


class FakeChatProvider:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def chat(self, model, messages, *, response_format=None):
        self.calls.append((model, messages, response_format))
        return self.response


class FakeEventSink:
    def __init__(self):
        self.events = []

    def record(self, event_type, payload):
        self.events.append((event_type, dict(payload)))


class CitedAnswerTest(unittest.TestCase):
    def test_supported_answer_resolves_citations_to_supplied_evidence(self):
        item = evidence()
        provider = FakeChatProvider(
            json.dumps(
                {
                    "answer": "Ollama was selected for local processing.",
                    "insufficient_evidence": False,
                    "citations": [item.segment_id],
                }
            )
        )
        retriever = FakeRetriever([item])
        composer = CitedAnswerComposer(
            retriever, provider, chat_model="gemma3:4b"
        )

        result = composer.ask("Why Ollama?", evidence_limit=4, view="decisions")

        self.assertFalse(result.insufficient_evidence)
        self.assertEqual((item,), result.citations)
        self.assertEqual([("Why Ollama?", 4)], retriever.calls)
        self.assertEqual("gemma3:4b", provider.calls[0][0])
        self.assertEqual(ANSWER_SCHEMA, provider.calls[0][2])
        prompt = provider.calls[0][1][1]["content"]
        self.assertIn(item.segment_id, prompt)
        self.assertIn(item.text, prompt)

    def test_empty_retrieval_declines_without_calling_chat_model(self):
        provider = FakeChatProvider("unused")
        composer = CitedAnswerComposer(
            FakeRetriever([]), provider, chat_model="gemma3:4b"
        )
        result = composer.ask("Unknown question")
        self.assertTrue(result.insufficient_evidence)
        self.assertEqual((), result.citations)
        self.assertEqual([], provider.calls)

    def test_unknown_citation_is_rejected(self):
        provider = FakeChatProvider(
            json.dumps(
                {
                    "answer": "Invented claim.",
                    "insufficient_evidence": False,
                    "citations": ["invented-segment"],
                }
            )
        )
        composer = CitedAnswerComposer(
            FakeRetriever([evidence()]), provider, chat_model="gemma3:4b"
        )
        with self.assertRaisesRegex(AnswerValidationError, "not supplied"):
            composer.ask("Question")

    def test_supported_answer_requires_a_citation(self):
        provider = FakeChatProvider(
            json.dumps(
                {
                    "answer": "Uncited claim.",
                    "insufficient_evidence": False,
                    "citations": [],
                }
            )
        )
        composer = CitedAnswerComposer(
            FakeRetriever([evidence()]), provider, chat_model="gemma3:4b"
        )
        with self.assertRaisesRegex(AnswerValidationError, "at least one"):
            composer.ask("Question")

    def test_events_hash_question_and_record_validation_failure(self):
        events = FakeEventSink()
        provider = FakeChatProvider("not json")
        composer = CitedAnswerComposer(
            FakeRetriever([evidence()]),
            provider,
            chat_model="gemma3:4b",
            event_sink=events,
        )
        question = "private customer question"
        with self.assertRaises(AnswerValidationError):
            composer.ask(question)
        self.assertEqual(
            ["answer.local.started", "answer.local.failed"],
            [event_type for event_type, _ in events.events],
        )
        self.assertNotIn(question, str(events.events))
        self.assertEqual("AnswerValidationError", events.events[-1][1]["error_type"])

    def test_cli_exposes_ask_and_prismatic_views(self):
        args = _build_parser().parse_args(
            [
                "ask",
                "--store",
                "semantic.sqlite3",
                "--view",
                "timeline",
                "What happened?",
            ]
        )
        self.assertEqual("ask", args.command)
        self.assertEqual("timeline", args.view)
        self.assertEqual("gemma3:4b", args.chat_model)
        self.assertEqual(120.0, args.timeout)


if __name__ == "__main__":
    unittest.main()
