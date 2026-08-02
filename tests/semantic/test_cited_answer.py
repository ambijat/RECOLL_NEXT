import json
import io
from pathlib import Path
import sys
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch


SEMANTIC_SOURCE = Path(__file__).resolve().parents[2] / "src" / "semantic"
sys.path.insert(0, str(SEMANTIC_SOURCE))

from recoll_ai import _build_parser, main as cli_main  # noqa: E402
from rclsem_answer import (  # noqa: E402
    ANSWER_SCHEMA,
    AnswerTimeout,
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
        response_schema = provider.calls[0][2]
        self.assertEqual(
            [item.segment_id],
            response_schema["properties"]["citations"]["items"]["enum"],
        )
        prompt = provider.calls[0][1][1]["content"]
        self.assertIn(item.segment_id, prompt)
        self.assertIn(item.text, prompt)

    def test_chat_schema_allows_only_supplied_unique_segment_ids(self):
        first = evidence("segment-1")
        second = evidence("segment-2")
        provider = FakeChatProvider(
            json.dumps(
                {
                    "answer": "The available evidence is insufficient.",
                    "insufficient_evidence": True,
                    "citations": [],
                }
            )
        )
        composer = CitedAnswerComposer(
            FakeRetriever([first, second, first]),
            provider,
            chat_model="gemma3:4b",
        )

        composer.ask("Question")

        response_schema = provider.calls[0][2]
        self.assertEqual(
            ["segment-1", "segment-2"],
            response_schema["properties"]["citations"]["items"]["enum"],
        )
        self.assertEqual(
            {"type": "string"},
            ANSWER_SCHEMA["properties"]["citations"]["items"],
        )

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

    def test_citation_resolution_does_not_verify_answer_is_grounded_in_evidence_text(self):
        """Documents a known gap: a valid, resolvable citation does not guarantee the
        generated prose is actually derived from that segment's text. The schema only
        constrains *which segment_id* may be cited, not whether the answer's claims
        are supported by that segment's content."""
        item = evidence()  # text: "Ollama remains local and the endpoint is configurable."
        fabricated_answer = (
            "Vladimir Putin addressed the Valdai Club on September 19, 2013 "
            "(source: http://eng.kremlin.ru/news/6007), and Alexander Dugin has "
            "been suggested as an influence on his Eurasian direction."
        )
        provider = FakeChatProvider(
            json.dumps(
                {
                    "answer": fabricated_answer,
                    "insufficient_evidence": False,
                    "citations": [item.segment_id],
                }
            )
        )
        composer = CitedAnswerComposer(
            FakeRetriever([item]), provider, chat_model="gemma3:4b"
        )

        result = composer.ask("Why Ollama?")

        # The composer accepts this answer: the cited segment_id resolves, so the
        # citation contract is technically satisfied, even though nothing in the
        # cited evidence text mentions Putin, Valdai, Kremlin.ru, or Dugin.
        self.assertEqual(fabricated_answer, result.answer)
        self.assertEqual((item,), result.citations)
        self.assertNotIn("Putin", item.text)

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
        self.assertEqual(900.0, args.max_runtime)

    def test_answer_progress_reports_stages_without_private_text(self):
        progress = []
        item = evidence()
        composer = CitedAnswerComposer(
            FakeRetriever([item]),
            FakeChatProvider(
                json.dumps(
                    {
                        "answer": "The endpoint remains local.",
                        "insufficient_evidence": False,
                        "citations": [item.segment_id],
                    }
                )
            ),
            chat_model="gemma3:4b",
            progress_callback=progress.append,
        )
        composer.ask("Why is the endpoint local?")
        self.assertEqual(
            [
                "retrieving_evidence",
                "generating_answer",
                "validating_citations",
                "completed",
            ],
            [entry["stage"] for entry in progress],
        )
        self.assertNotIn(item.text, str(progress))

    def test_cli_keyboard_interrupt_is_a_clean_cancelled_exit(self):
        output = io.StringIO()
        with patch("recoll_ai._run_sync", side_effect=KeyboardInterrupt), redirect_stdout(output):
            code = cli_main(["sync", "--store", "practice.sqlite3"])
        self.assertEqual(130, code)
        self.assertIn("cancelled", output.getvalue().lower())
        self.assertNotIn("Traceback", output.getvalue())

    def test_answer_total_runtime_expires_after_bounded_model_request(self):
        clock = [0.0]
        item = evidence()

        class SlowChat(FakeChatProvider):
            def chat(self, *args, **kwargs):
                clock[0] = 2.0
                return super().chat(*args, **kwargs)

        composer = CitedAnswerComposer(
            FakeRetriever([item]),
            SlowChat(
                json.dumps(
                    {
                        "answer": "Supported.",
                        "insufficient_evidence": False,
                        "citations": [item.segment_id],
                    }
                )
            ),
            chat_model="gemma3:4b",
            clock=lambda: clock[0],
        )
        with self.assertRaises(AnswerTimeout):
            composer.ask("Question?", max_runtime_seconds=1)


if __name__ == "__main__":
    unittest.main()
