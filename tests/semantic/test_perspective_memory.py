from pathlib import Path
import sys
import tempfile
import unittest


SEMANTIC_SOURCE = Path(__file__).resolve().parents[2] / "src" / "semantic"
sys.path.insert(0, str(SEMANTIC_SOURCE))

from recoll_ai import _build_parser  # noqa: E402
from rclsem_perspectives import (  # noqa: E402
    PerspectiveCitation,
    PerspectiveMemory,
    PerspectiveMemoryError,
)
from rclsem_segments import SourceDocument, TextSegment  # noqa: E402
from rclsem_store import SemanticStore  # noqa: E402


class PerspectiveMemoryTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = Path(self.tempdir.name) / "semantic.sqlite3"
        self.semantic = SemanticStore(self.path)
        namespace = self.semantic.ensure_namespace("embeddinggemma", "segmenter-v1")
        self.namespace_id = namespace.namespace_id
        document = SourceDocument(
            document_id="rcludi-1",
            text="Local evidence remains authoritative.",
            title="Protocol",
            path="docs/PROTOCOL.md",
        )
        revision = document.revision()
        segment = TextSegment(
            segment_id="segment-1",
            document_id=document.document_id,
            source_revision=revision,
            ordinal=0,
            source_start=0,
            source_end=len(document.text),
            text=document.text,
            segmenter_version="segmenter-v1",
        )
        self.semantic.replace_document(
            self.namespace_id, document, [segment], [[1.0, 0.0, 0.0]]
        )
        self.citation = PerspectiveCitation(
            segment_id=segment.segment_id,
            document_id=document.document_id,
            source_revision=revision,
        )
        self.memory = PerspectiveMemory(self.path)

    def tearDown(self):
        self.tempdir.cleanup()

    def remember(self, embedding=(0.9, 0.1, 0.0)):
        return self.memory.remember(
            question="Why is Xapian authoritative?",
            answer="It owns lexical evidence and document identity.",
            view="decisions",
            chat_model="gemma3:4b",
            embedding_model="embeddinggemma",
            citations=[self.citation],
            embedding=embedding,
        )

    def test_remembers_and_semantically_retrieves_a_cited_perspective(self):
        identity = self.remember()

        results = self.memory.search(
            [1.0, 0.0, 0.0], embedding_model="embeddinggemma", limit=3
        )

        self.assertEqual(1, len(results))
        self.assertEqual(identity, results[0].perspective_id)
        self.assertEqual((self.citation,), results[0].citations)
        self.assertGreater(results[0].similarity, 0.99)

    def test_exact_duplicate_is_deduplicated(self):
        self.assertEqual(self.remember(), self.remember())
        self.assertEqual(1, self.memory.count())

    def test_stale_source_revision_suppresses_secondary_memory(self):
        self.remember()
        self.semantic.delete_documents_not_in(self.namespace_id, set())

        results = self.memory.search(
            [1.0, 0.0, 0.0], embedding_model="embeddinggemma"
        )

        self.assertEqual([], results)

    def test_requires_primary_citations_and_compatible_dimensions(self):
        with self.assertRaisesRegex(PerspectiveMemoryError, "cite primary evidence"):
            self.memory.remember(
                question="Question",
                answer="Answer",
                view="answer",
                chat_model="gemma3:4b",
                embedding_model="embeddinggemma",
                citations=[],
                embedding=[1.0, 0.0],
            )
        self.remember()
        with self.assertRaisesRegex(PerspectiveMemoryError, "expects 3 dimensions"):
            self.memory.search([1.0, 0.0], embedding_model="embeddinggemma")

    def test_cli_enables_memory_by_default_and_exposes_search(self):
        ask = _build_parser().parse_args(
            ["ask", "--store", "semantic.sqlite3", "Question"]
        )
        private = _build_parser().parse_args(
            ["ask", "--store", "semantic.sqlite3", "--no-remember", "Question"]
        )
        search = _build_parser().parse_args(
            ["memory-search", "--store", "semantic.sqlite3", "local policy"]
        )

        self.assertTrue(ask.remember)
        self.assertFalse(private.remember)
        self.assertEqual("memory-search", search.command)
        self.assertEqual(5, search.limit)


if __name__ == "__main__":
    unittest.main()
