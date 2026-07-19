from pathlib import Path
import hashlib
import sys
import tempfile
import unittest


SEMANTIC_SOURCE = Path(__file__).resolve().parents[2] / "src" / "semantic"
sys.path.insert(0, str(SEMANTIC_SOURCE))

from rclsem_recoll import (  # noqa: E402
    RecollInventory,
    RecollInventoryError,
    _decode_bridge_document,
)
from rclsem_retrieve import SemanticRetrievalError, SemanticSearcher  # noqa: E402
from rclsem_segments import DeterministicSegmenter, SourceDocument  # noqa: E402
from rclsem_store import SemanticStore, StoreCompatibilityError  # noqa: E402
from rclsem_sync import SemanticSynchronizer  # noqa: E402


class FakeResult:
    def __init__(self, rcludi, text, title="", url="", filename=""):
        self.rcludi = rcludi
        self.text = text
        self.title = title
        self.url = url
        self.filename = filename


class FakeQuery:
    def __init__(self, results):
        self.results = results
        self.executed = None

    def execute(self, query, *, fetchtext=False):
        self.executed = (query, fetchtext)

    def __iter__(self):
        return iter(self.results)


class FakeDatabase:
    def __init__(self, query):
        self._query = query

    def query(self):
        return self._query


class RecollInventoryTest(unittest.TestCase):
    def test_inventory_requests_text_and_maps_stable_source_fields(self):
        query = FakeQuery(
            [FakeResult(b"udi-1", b"local body", "Title", "file:///notes/a.txt")]
        )
        confdirs = []
        inventory = RecollInventory(
            confdir="profile",
            connector=lambda confdir: confdirs.append(confdir) or FakeDatabase(query),
        )

        documents = list(inventory.documents())

        self.assertEqual(["profile"], confdirs)
        self.assertEqual(("mime:*", True), query.executed)
        self.assertEqual(
            SourceDocument(
                "udi-1", "local body", title="Title", path="file:///notes/a.txt"
            ),
            documents[0],
        )

    def test_inventory_falls_back_to_filename(self):
        query = FakeQuery([FakeResult("udi", "body", filename="C:/notes/a.txt")])
        inventory = RecollInventory(connector=lambda _: FakeDatabase(query))
        self.assertEqual("C:/notes/a.txt", next(inventory.documents()).path)

    def test_missing_stable_identifier_is_rejected(self):
        query = FakeQuery([FakeResult("", "private body")])
        inventory = RecollInventory(connector=lambda _: FakeDatabase(query))
        with self.assertRaisesRegex(RecollInventoryError, "rcludi"):
            list(inventory.documents())

    def test_bridge_json_maps_to_the_same_source_contract(self):
        document = _decode_bridge_document(
            '{"document_id":"udi","text":"body","title":"T","path":"p"}\n',
            1,
        )
        self.assertEqual(SourceDocument("udi", "body", title="T", path="p"), document)

    def test_bridge_rejects_malformed_or_extra_fields(self):
        with self.assertRaisesRegex(RecollInventoryError, "invalid JSON"):
            _decode_bridge_document("not-json\n", 2)
        with self.assertRaisesRegex(RecollInventoryError, "invalid fields"):
            _decode_bridge_document(
                '{"document_id":"udi","text":"body","title":"T",'
                '"path":"p","secret":"x"}\n',
                3,
            )


class FakeEventSink:
    def __init__(self):
        self.events = []

    def record(self, event_type, payload):
        self.events.append((event_type, dict(payload)))


class MeaningEmbeddingProvider:
    def embed(self, model, inputs):
        values = [inputs] if isinstance(inputs, str) else list(inputs)
        vectors = []
        for value in values:
            lowered = value.lower()
            if "governance" in lowered or "integrity" in lowered:
                vectors.append([1.0, 0.0, 0.0])
            elif "recipe" in lowered or "kitchen" in lowered:
                vectors.append([0.0, 1.0, 0.0])
            else:
                vectors.append([0.0, 0.0, 1.0])
        return vectors


class SemanticRetrievalTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.store = SemanticStore(Path(self.tempdir.name) / "semantic.sqlite3")
        self.provider = MeaningEmbeddingProvider()
        self.sync = SemanticSynchronizer(
            self.store,
            self.provider,
            embedding_model="embeddinggemma",
            segmenter=DeterministicSegmenter(),
        )
        self.sync.sync(
            [
                SourceDocument(
                    "policy",
                    "Governance preserves evidence integrity and cited decisions.",
                    title="Governance",
                    path="docs/governance.md",
                ),
                SourceDocument(
                    "food",
                    "A kitchen recipe explains how to prepare soup.",
                    title="Recipe",
                    path="notes/recipe.txt",
                ),
            ]
        )

    def test_exact_cosine_search_returns_source_evidence(self):
        searcher = SemanticSearcher(
            self.store, self.provider, embedding_model="embeddinggemma"
        )
        results = searcher.search("integrity of cited evidence", limit=2)
        self.assertEqual("policy", results[0].document_id)
        self.assertEqual("docs/governance.md", results[0].path)
        self.assertEqual(1.0, results[0].similarity)
        self.assertEqual(
            "Governance preserves evidence integrity and cited decisions.",
            results[0].text,
        )

    def test_ties_are_broken_by_stable_segment_identity(self):
        searcher = SemanticSearcher(
            self.store, self.provider, embedding_model="embeddinggemma"
        )
        results = searcher.search("unmapped neutral query", limit=2)
        self.assertEqual(
            sorted(result.segment_id for result in results),
            [result.segment_id for result in results],
        )

    def test_search_events_hash_query_and_never_record_raw_text(self):
        events = FakeEventSink()
        searcher = SemanticSearcher(
            self.store,
            self.provider,
            embedding_model="embeddinggemma",
            event_sink=events,
        )
        query = "private integrity question"
        results = searcher.search(query, limit=1)
        self.assertEqual(
            ["search.semantic.started", "search.semantic.completed"],
            [event_type for event_type, _ in events.events],
        )
        self.assertNotIn(query, str(events.events))
        self.assertEqual(
            hashlib.sha256(query.encode("utf-8")).hexdigest(),
            events.events[0][1]["query_sha256"],
        )
        self.assertEqual([results[0].segment_id], events.events[-1][1]["segment_ids"])

    def test_query_dimension_mismatch_is_rejected(self):
        class WrongDimensions:
            def embed(self, model, inputs):
                return [[1.0, 0.0]]

        searcher = SemanticSearcher(
            self.store, WrongDimensions(), embedding_model="embeddinggemma"
        )
        with self.assertRaises(StoreCompatibilityError):
            searcher.search("question")

    def test_empty_query_and_nonpositive_limit_are_rejected(self):
        searcher = SemanticSearcher(
            self.store, self.provider, embedding_model="embeddinggemma"
        )
        with self.assertRaises(SemanticRetrievalError):
            searcher.search(" ")
        with self.assertRaises(SemanticRetrievalError):
            searcher.search("question", limit=0)


if __name__ == "__main__":
    unittest.main()
