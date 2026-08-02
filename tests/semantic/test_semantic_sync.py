from pathlib import Path
import sys
import tempfile
import unittest


SEMANTIC_SOURCE = Path(__file__).resolve().parents[2] / "src" / "semantic"
sys.path.insert(0, str(SEMANTIC_SOURCE))

from rclsem_segments import (  # noqa: E402
    DeterministicSegmenter,
    SEGMENTER_VERSION,
    SegmenterConfig,
    SourceDocument,
)
from rclsem_store import SemanticStore, StoreCompatibilityError  # noqa: E402
from rclsem_sync import (  # noqa: E402
    SemanticSynchronizer,
    SynchronizationError,
    SynchronizationTimeout,
)


class FakeEventSink:
    def __init__(self):
        self.events = []

    def record(self, event_type, payload):
        self.events.append((event_type, dict(payload)))


class FakeEmbeddingProvider:
    def __init__(self, dimensions=3):
        self.dimensions = dimensions
        self.calls = []

    def embed(self, model, inputs):
        batch = list(inputs)
        self.calls.append((model, batch))
        return [
            [float(len(text)), float(index + 1)]
            + [0.25] * (self.dimensions - 2)
            for index, text in enumerate(batch)
        ]

    @property
    def embedded_count(self):
        return sum(len(batch) for _, batch in self.calls)


class FakeClock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


class SegmenterTest(unittest.TestCase):
    def setUp(self):
        self.segmenter = DeterministicSegmenter(
            SegmenterConfig(target_chars=90, overlap_chars=20)
        )
        self.document = SourceDocument(
            document_id="doc-1",
            title="Deployment notes",
            path="notes/deployment.txt",
            text=(
                "The release was initially planned for Monday. "
                "Security approval remained outstanding for several days. "
                "The team moved deployment into the following week. "
                "Validation then completed successfully."
            ),
        )

    def test_segmentation_is_deterministic_and_source_preserving(self):
        first = self.segmenter.segment(self.document)
        second = self.segmenter.segment(self.document)
        self.assertEqual(first, second)
        self.assertGreater(len(first), 1)
        self.assertEqual(list(range(len(first))), [segment.ordinal for segment in first])
        for segment in first:
            source_slice = self.document.text[segment.source_start : segment.source_end]
            self.assertEqual(segment.text, " ".join(source_slice.split()))
            self.assertEqual(SEGMENTER_VERSION, segment.segmenter_version)

    def test_adjacent_segments_overlap(self):
        segments = self.segmenter.segment(self.document)
        for left, right in zip(segments, segments[1:]):
            self.assertLess(right.source_start, left.source_end)
            self.assertGreater(right.source_start, left.source_start)

    def test_content_or_metadata_change_changes_revision_and_segment_ids(self):
        original = self.segmenter.segment(self.document)
        changed = self.segmenter.segment(
            SourceDocument(
                document_id=self.document.document_id,
                title="Changed title",
                path=self.document.path,
                text=self.document.text,
            )
        )
        self.assertNotEqual(original[0].source_revision, changed[0].source_revision)
        self.assertNotEqual(original[0].segment_id, changed[0].segment_id)

    def test_empty_text_has_no_segments(self):
        self.assertEqual([], self.segmenter.segment(SourceDocument("empty", " \n\t")))


class SemanticSyncTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.store = SemanticStore(Path(self.tempdir.name) / "semantic.sqlite3")
        self.provider = FakeEmbeddingProvider()
        self.segmenter = DeterministicSegmenter(
            SegmenterConfig(target_chars=80, overlap_chars=16)
        )
        self.synchronizer = SemanticSynchronizer(
            self.store,
            self.provider,
            embedding_model="embeddinggemma",
            segmenter=self.segmenter,
            batch_size=2,
        )
        self.first = SourceDocument(
            "doc-1",
            "Alpha planning began early. " * 8,
            title="Alpha",
            path="alpha.txt",
        )
        self.second = SourceDocument(
            "doc-2",
            "Beta validation finished later. " * 5,
            title="Beta",
            path="beta.txt",
        )

    def test_first_sync_batches_and_persists_segments(self):
        report = self.synchronizer.sync([self.first, self.second])
        self.assertEqual(2, report.documents_added)
        self.assertEqual(0, report.documents_updated)
        self.assertEqual(self.provider.embedded_count, report.segments_embedded)
        self.assertTrue(all(len(batch) <= 2 for _, batch in self.provider.calls))
        documents, segments = self.store.counts(report.namespace_id)
        self.assertEqual(2, documents)
        self.assertEqual(report.segments_embedded, segments)
        namespace = self.store.get_namespace(report.namespace_id)
        self.assertEqual(3, namespace.dimensions)
        stored = self.store.read_document_segments(report.namespace_id, "doc-1")
        self.assertTrue(stored)
        self.assertEqual(3, len(stored[0].embedding))

    def test_repeated_sync_is_idempotent(self):
        first_report = self.synchronizer.sync([self.first, self.second])
        calls_after_first = len(self.provider.calls)
        second_report = self.synchronizer.sync([self.first, self.second])
        self.assertEqual(0, second_report.documents_added)
        self.assertEqual(0, second_report.documents_updated)
        self.assertEqual(2, second_report.documents_unchanged)
        self.assertEqual(0, second_report.segments_embedded)
        self.assertEqual(calls_after_first, len(self.provider.calls))
        self.assertEqual(
            self.store.counts(first_report.namespace_id),
            self.store.counts(second_report.namespace_id),
        )

    def test_changed_document_is_replaced_and_missing_document_deleted(self):
        first_report = self.synchronizer.sync([self.first, self.second])
        changed = SourceDocument(
            "doc-1",
            self.first.text + "A final approval was recorded.",
            title=self.first.title,
            path=self.first.path,
        )
        report = self.synchronizer.sync([changed])
        self.assertEqual(0, report.documents_added)
        self.assertEqual(1, report.documents_updated)
        self.assertEqual(1, report.documents_deleted)
        self.assertEqual((1, report.segments_embedded), self.store.counts(report.namespace_id))
        revisions = self.store.document_revisions(first_report.namespace_id)
        self.assertEqual({"doc-1": changed.revision()}, revisions)

    def test_changed_model_creates_an_independent_namespace(self):
        first_report = self.synchronizer.sync([self.first])
        second_sync = SemanticSynchronizer(
            self.store,
            self.provider,
            embedding_model="another-embedding-model",
            segmenter=self.segmenter,
        )
        second_report = second_sync.sync([self.first])
        self.assertNotEqual(first_report.namespace_id, second_report.namespace_id)
        self.assertEqual((1, first_report.segments_embedded), self.store.counts(first_report.namespace_id))
        self.assertEqual((1, second_report.segments_embedded), self.store.counts(second_report.namespace_id))

    def test_dimension_change_is_rejected_without_replacing_document(self):
        report = self.synchronizer.sync([self.first])
        original_revision = self.first.revision()
        changed = SourceDocument("doc-1", self.first.text + " changed")
        self.provider.dimensions = 2
        with self.assertRaises(StoreCompatibilityError):
            self.synchronizer.sync([changed])
        self.assertEqual(
            original_revision,
            self.store.document_revisions(report.namespace_id)["doc-1"],
        )

    def test_duplicate_document_ids_are_rejected(self):
        with self.assertRaisesRegex(SynchronizationError, "duplicate"):
            self.synchronizer.sync([self.first, self.first])

    def test_sync_records_privacy_safe_lifecycle_events(self):
        events = FakeEventSink()
        synchronizer = SemanticSynchronizer(
            self.store,
            self.provider,
            embedding_model="embeddinggemma",
            segmenter=self.segmenter,
            event_sink=events,
        )
        report = synchronizer.sync([self.first])
        self.assertEqual(
            ["index.semantic.started", "index.semantic.completed"],
            [event_type for event_type, _ in events.events],
        )
        encoded_events = str(events.events)
        self.assertNotIn(self.first.text, encoded_events)
        self.assertEqual(
            report.segments_embedded,
            events.events[-1][1]["segments_embedded"],
        )

    def test_failure_records_only_the_error_type(self):
        events = FakeEventSink()
        synchronizer = SemanticSynchronizer(
            self.store,
            self.provider,
            embedding_model="embeddinggemma",
            segmenter=self.segmenter,
            event_sink=events,
        )
        with self.assertRaises(SynchronizationError):
            synchronizer.sync([self.first, self.first])
        self.assertEqual("index.semantic.failed", events.events[-1][0])
        self.assertEqual(
            {"namespace_id", "error_type"}, set(events.events[-1][1])
        )

    def test_progress_reports_document_and_batch_boundaries_without_content(self):
        progress = []
        synchronizer = SemanticSynchronizer(
            self.store,
            self.provider,
            embedding_model="embeddinggemma",
            segmenter=self.segmenter,
            batch_size=2,
            progress_callback=progress.append,
        )
        report = synchronizer.sync([self.first])
        stages = [item["stage"] for item in progress]
        self.assertIn("document_started", stages)
        self.assertIn("batch_completed", stages)
        self.assertIn("document_completed", stages)
        self.assertEqual("completed", stages[-1])
        self.assertEqual(report.segments_embedded, progress[-1]["segments_embedded"])
        self.assertNotIn(self.first.text, str(progress))
        self.assertNotIn(self.first.path, str(progress))

    def test_total_runtime_expires_at_batch_boundary_without_partial_document(self):
        clock = FakeClock()

        class SlowProvider(FakeEmbeddingProvider):
            def embed(inner_self, model, inputs):
                result = super(SlowProvider, inner_self).embed(model, inputs)
                clock.advance(2)
                return result

        synchronizer = SemanticSynchronizer(
            self.store,
            SlowProvider(),
            embedding_model="embeddinggemma",
            segmenter=self.segmenter,
            batch_size=1,
            clock=clock,
        )
        with self.assertRaises(SynchronizationTimeout):
            synchronizer.sync([self.first], max_runtime_seconds=1)
        namespace = self.store.ensure_namespace(
            "embeddinggemma", self.segmenter.version
        )
        self.assertEqual((0, 0), self.store.counts(namespace.namespace_id))


if __name__ == "__main__":
    unittest.main()
