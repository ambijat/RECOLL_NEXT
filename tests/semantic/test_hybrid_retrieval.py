from pathlib import Path
import hashlib
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


SEMANTIC_SOURCE = Path(__file__).resolve().parents[2] / "src" / "semantic"
sys.path.insert(0, str(SEMANTIC_SOURCE))

from recoll_ai import _RankedEvidenceRetriever, _build_parser, _run_search  # noqa: E402
from rclsem_hybrid import (  # noqa: E402
    HybridSearchCoordinator,
    LexicalSearcher,
    SearchEvidence,
)
from rclsem_recoll import RecollQueryService  # noqa: E402
from rclsem_retrieve import EvidenceResult  # noqa: E402
from rclsem_segments import DeterministicSegmenter, SourceDocument  # noqa: E402


class FakeEventSink:
    def __init__(self):
        self.events = []

    def record(self, event_type, payload):
        self.events.append((event_type, dict(payload)))


class FakeDocuments:
    def __init__(self, lexical, live=None):
        self.lexical = lexical
        self.live = {item.document_id: item for item in (live or lexical)}
        self.queries = []
        self.resolutions = []

    def search(self, query_text, *, limit):
        self.queries.append((query_text, limit))
        return self.lexical[:limit]

    def resolve(self, document_ids):
        identities = tuple(document_ids)
        self.resolutions.append(identities)
        return {item: self.live[item] for item in identities if item in self.live}


class FakeSemantic:
    def __init__(self, results=None, error=None):
        self.results = results or []
        self.error = error
        self.calls = []

    def search(self, query, *, limit=10):
        self.calls.append((query, limit))
        if self.error:
            raise self.error
        return self.results[:limit]


def semantic_evidence(document, *, score=0.9, revision=None):
    segment = DeterministicSegmenter().segment(document)[0]
    return EvidenceResult(
        segment_id=segment.segment_id,
        document_id=document.document_id,
        source_revision=revision or segment.source_revision,
        title=document.title,
        path=document.path,
        text=segment.text,
        source_start=segment.source_start,
        source_end=segment.source_end,
        similarity=score,
    )


class HybridRetrievalTest(unittest.TestCase):
    def setUp(self):
        self.alpha = SourceDocument(
            "alpha", "A governance protocol records decisions and evidence.", "Alpha", "a.md"
        )
        self.beta = SourceDocument(
            "beta", "A kitchen notebook includes a soup recipe.", "Beta", "b.md"
        )

    def test_exact_preserves_xapian_order_and_does_not_call_semantic(self):
        documents = FakeDocuments([self.beta, self.alpha])
        semantic = FakeSemantic(error=AssertionError("must not be called"))
        coordinator = HybridSearchCoordinator(
            LexicalSearcher(documents), documents, semantic
        )

        report = coordinator.search("title:recipe", mode="exact", limit=2)

        self.assertEqual(["beta", "alpha"], [item.document_id for item in report.results])
        self.assertEqual(("title:recipe", 2), documents.queries[0])
        self.assertEqual([], semantic.calls)
        self.assertEqual([1, 2], [item.lexical_rank for item in report.results])

    def test_prismatic_rrf_includes_both_channels_and_deduplicates_documents(self):
        documents = FakeDocuments([self.alpha, self.beta])
        semantic = FakeSemantic(
            [semantic_evidence(self.beta), semantic_evidence(self.alpha, score=0.8)]
        )
        coordinator = HybridSearchCoordinator(
            LexicalSearcher(documents), documents, semantic, candidate_limit=2
        )

        report = coordinator.search("governance", mode="prismatic", limit=2)

        self.assertEqual(2, len(report.results))
        self.assertEqual({"alpha", "beta"}, {item.document_id for item in report.results})
        for item in report.results:
            self.assertEqual(("lexical", "semantic"), item.provenance)
            self.assertIsNotNone(item.fusion_score)
            self.assertEqual("prismatic", item.retrieval_mode)

    def test_stale_semantic_evidence_is_rejected_against_live_recoll_revision(self):
        documents = FakeDocuments([self.alpha])
        semantic = FakeSemantic([semantic_evidence(self.alpha, revision="stale")])
        coordinator = HybridSearchCoordinator(
            LexicalSearcher(documents), documents, semantic
        )

        conceptual = coordinator.search("governance", mode="conceptual", limit=3)
        prismatic = coordinator.search("governance", mode="prismatic", limit=3)

        self.assertEqual(1, conceptual.stale_rejected)
        self.assertEqual((), conceptual.results)
        self.assertEqual(1, prismatic.stale_rejected)
        self.assertEqual(["alpha"], [item.document_id for item in prismatic.results])
        self.assertEqual(("lexical",), prismatic.results[0].provenance)

    def test_prismatic_degrades_to_lexical_when_semantic_provider_fails(self):
        documents = FakeDocuments([self.alpha])
        semantic = FakeSemantic(error=ConnectionError("Ollama offline"))
        coordinator = HybridSearchCoordinator(
            LexicalSearcher(documents), documents, semantic
        )

        report = coordinator.search("governance", mode="prismatic", limit=1)

        self.assertTrue(report.degraded)
        self.assertEqual("ConnectionError", report.semantic_error_type)
        self.assertEqual("alpha", report.results[0].document_id)

    def test_events_hash_query_and_never_record_raw_query(self):
        events = FakeEventSink()
        documents = FakeDocuments([self.alpha])
        coordinator = HybridSearchCoordinator(
            LexicalSearcher(documents, event_sink=events),
            documents,
            FakeSemantic([semantic_evidence(self.alpha)]),
            event_sink=events,
        )
        query = "private governance constraint"

        coordinator.search(query, mode="prismatic", limit=1)

        self.assertNotIn(query, str(events.events))
        self.assertEqual(
            hashlib.sha256(query.encode("utf-8")).hexdigest(),
            events.events[0][1]["query_sha256"],
        )

    def test_selected_visible_evidence_is_revalidated_by_rank_and_identity(self):
        results = [
            SearchEvidence(
                segment_id=f"segment-{position}",
                document_id=f"document-{position}",
                source_revision="revision",
                title=f"Document {position}",
                path=f"{position}.md",
                text="Evidence",
                source_start=0,
                source_end=8,
                similarity=None,
                retrieval_mode="exact",
                provenance=("lexical",),
                lexical_rank=position,
            )
            for position in range(1, 4)
        ]

        class Coordinator:
            def search(self, query, *, mode, limit):
                self.call = (query, mode, limit)
                return SimpleNamespace(results=tuple(results[:limit]))

        coordinator = Coordinator()
        retriever = _RankedEvidenceRetriever(
            coordinator,
            mode="exact",
            ranks=(2,),
            expected_segment_ids=("segment-2",),
        )

        selected = retriever.search("question", limit=1)

        self.assertEqual(["segment-2"], [item.segment_id for item in selected])
        self.assertEqual(("question", "exact", 2), coordinator.call)

    def test_selected_visible_evidence_fails_closed_when_result_changed(self):
        result = SearchEvidence(
            segment_id="new-segment",
            document_id="document",
            source_revision="revision",
            title="Document",
            path="document.md",
            text="Evidence",
            source_start=0,
            source_end=8,
            similarity=None,
            retrieval_mode="exact",
            provenance=("lexical",),
            lexical_rank=1,
        )

        class Coordinator:
            def search(self, query, *, mode, limit):
                return SimpleNamespace(results=(result,))

        retriever = _RankedEvidenceRetriever(
            Coordinator(),
            mode="exact",
            ranks=(1,),
            expected_segment_ids=("old-segment",),
        )

        with self.assertRaisesRegex(ValueError, "run Find Evidence again"):
            retriever.search("question", limit=1)


class FakeResult:
    def __init__(self, document):
        self.rcludi = document.document_id
        self.text = document.text
        self.title = document.title
        self.url = document.path
        self.filename = ""


class FakeQuery:
    def __init__(self, results):
        self.results = results
        self.executed = None

    def execute(self, query, *, fetchtext=False):
        self.executed = (query, fetchtext)

    def __iter__(self):
        return iter(self.results)


class FakeDatabase:
    def __init__(self, documents):
        self.documents = {item.document_id: item for item in documents}
        self.last_query = None

    def query(self):
        self.last_query = FakeQuery([FakeResult(item) for item in self.documents.values()])
        return self.last_query

    def getDoc(self, document_id):
        if document_id not in self.documents:
            raise AttributeError(document_id)
        return FakeResult(self.documents[document_id])


class RecollQueryServiceTest(unittest.TestCase):
    def test_bounded_search_and_private_resolution_use_live_recoll(self):
        documents = [
            SourceDocument("one", "first body", "One", "one.md"),
            SourceDocument("two", "second body", "Two", "two.md"),
        ]
        database = FakeDatabase(documents)
        service = RecollQueryService(confdir="profile", connector=lambda _: database)

        results = service.search("title:one", limit=1)
        resolved = service.resolve(["two", "missing"])

        self.assertEqual(["one"], [item.document_id for item in results])
        self.assertEqual(("title:one", True), database.last_query.executed)
        self.assertEqual(["two"], list(resolved))

    def test_lexical_search_skips_hits_without_stable_identity(self):
        valid = SourceDocument("valid", "searchable body", "Valid", "valid.md")
        query = FakeQuery(
            [FakeResult(SourceDocument("", "container result")), FakeResult(valid)]
        )

        class QueryDatabase:
            def query(self):
                return query

        service = RecollQueryService(connector=lambda _: QueryDatabase())

        results = service.search("searchable", limit=1)

        self.assertEqual(["valid"], [item.document_id for item in results])


class SearchCliContractTest(unittest.TestCase):
    def test_exact_parser_does_not_require_semantic_store(self):
        args = _build_parser().parse_args(["search", "--mode", "exact", "term"])
        self.assertIsNone(args.store)

    def test_exact_execution_does_not_construct_ollama_or_semantic_store(self):
        args = _build_parser().parse_args(["search", "--mode", "exact", "term"])
        document = SourceDocument("one", "term body", "One", "one.md")
        with patch("rclsem_recoll.RecollQueryService.search", return_value=[document]), patch(
            "recoll_ai.OllamaClient", side_effect=AssertionError("must not construct Ollama")
        ):
            report = _run_search(args)

        self.assertEqual("exact", report["mode"])
        self.assertEqual("one", report["results"][0]["document_id"])

    def test_prismatic_missing_store_degrades_without_creating_sqlite(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Path(directory) / "missing.sqlite3"
            args = _build_parser().parse_args(
                ["search", "--mode", "prismatic", "--store", str(store), "term"]
            )
            document = SourceDocument("one", "term body", "One", "one.md")
            with patch(
                "rclsem_recoll.RecollQueryService.search", return_value=[document]
            ):
                report = _run_search(args)

            self.assertTrue(report["degraded"])
            self.assertEqual("FileNotFoundError", report["semantic_error_type"])
            self.assertFalse(store.exists())

    def test_ask_parser_accepts_mode_and_visible_evidence_selection(self):
        args = _build_parser().parse_args(
            [
                "ask",
                "--store",
                "semantic.sqlite3",
                "--mode",
                "prismatic",
                "--evidence-rank",
                "2",
                "--expected-segment-id",
                "segment-2",
                "question",
            ]
        )

        self.assertEqual("prismatic", args.mode)
        self.assertEqual([2], args.evidence_rank)
        self.assertEqual(["segment-2"], args.expected_segment_id)


if __name__ == "__main__":
    unittest.main()
