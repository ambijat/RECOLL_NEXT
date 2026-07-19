import json
from pathlib import Path
import sys
import tempfile
import unittest


SEMANTIC_SOURCE = Path(__file__).resolve().parents[2] / "src" / "semantic"
sys.path.insert(0, str(SEMANTIC_SOURCE))

from rclsem_ledger import (  # noqa: E402
    EventLedger,
    GENESIS_HASH,
    LedgerError,
    LedgerVerificationError,
)


class EventLedgerTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.path = Path(self.tempdir.name) / "events.jsonl"
        self.ledger = EventLedger(self.path)

    def test_empty_ledger_is_valid(self):
        report = self.ledger.verify()
        self.assertEqual(0, report.event_count)
        self.assertEqual(GENESIS_HASH, report.head_hash)

    def test_append_builds_a_verifiable_chain(self):
        first = self.ledger.append(
            "session.started",
            actor="recoll-next",
            session_id="session-1",
            payload={"purpose": "test", "nested": {"value": 2}},
            timestamp="2026-07-19T00:00:00.000Z",
        )
        second = self.ledger.append(
            "search.semantic.completed",
            actor="semantic-worker",
            session_id="session-1",
            payload={"result_count": 3},
            timestamp="2026-07-19T00:00:01.000Z",
        )

        self.assertEqual(1, first["sequence"])
        self.assertEqual(GENESIS_HASH, first["previous_hash"])
        self.assertEqual(first["hash"], second["previous_hash"])
        report = self.ledger.verify()
        self.assertEqual(2, report.event_count)
        self.assertEqual(second["hash"], report.head_hash)
        self.assertEqual((first, second), self.ledger.read_verified())

    def test_payload_is_serialized_canonically(self):
        event = self.ledger.append(
            "config.changed",
            actor="operator",
            session_id="session-2",
            payload={"z": 1, "a": "é"},
        )
        line = self.path.read_text(encoding="utf-8")
        self.assertIn('"payload":{"a":"é","z":1}', line)
        self.assertEqual(event, json.loads(line))

    def test_mutation_is_detected(self):
        self.ledger.append(
            "session.started",
            actor="recoll-next",
            session_id="session-3",
            payload={"state": "original"},
        )
        content = self.path.read_text(encoding="utf-8")
        self.path.write_text(
            content.replace('"state":"original"', '"state":"changed"'),
            encoding="utf-8",
            newline="\n",
        )

        with self.assertRaisesRegex(LedgerVerificationError, "event hash"):
            self.ledger.verify()

    def test_append_refuses_a_damaged_chain(self):
        self.path.write_text("not json\n", encoding="utf-8", newline="\n")
        with self.assertRaises(LedgerVerificationError):
            self.ledger.append(
                "session.started",
                actor="recoll-next",
                session_id="session-4",
            )

    def test_rejects_unstructured_event_names_and_payloads(self):
        with self.assertRaises(LedgerError):
            self.ledger.append(
                "started", actor="recoll-next", session_id="session-5"
            )
        with self.assertRaises(LedgerError):
            self.ledger.append(
                "session.started",
                actor="recoll-next",
                session_id="session-5",
                payload=["not", "an", "object"],
            )

    def test_rejects_non_utc_timestamp(self):
        with self.assertRaisesRegex(LedgerError, "UTC"):
            self.ledger.append(
                "session.started",
                actor="recoll-next",
                session_id="session-6",
                timestamp="2026-07-19T12:00:00+05:30",
            )


if __name__ == "__main__":
    unittest.main()
