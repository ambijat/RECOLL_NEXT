from pathlib import Path
import sys
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SEMANTIC_SOURCE = REPOSITORY_ROOT / "src" / "semantic"
sys.path.insert(0, str(SEMANTIC_SOURCE))

from rclsem_ledger import EventLedger  # noqa: E402


class ProjectGovernanceLedgerTest(unittest.TestCase):
    def setUp(self):
        self.ledger = EventLedger(REPOSITORY_ROOT / "governance" / "events.jsonl")

    def test_project_chain_verifies_from_genesis(self):
        report = self.ledger.verify()
        self.assertGreaterEqual(report.event_count, 6)
        self.assertEqual(64, len(report.head_hash))

    def test_original_goal_remains_the_genesis_event(self):
        events = self.ledger.read_verified()
        self.assertEqual("project.goal.established", events[0]["event_type"])
        principles = events[0]["payload"]["principles"]
        self.assertIn("ollama-local-only", principles)
        self.assertIn("evidence-citations", principles)
        self.assertIn("lexical-fallback", principles)

    def test_current_head_is_recorded_as_a_human_readable_checkpoint(self):
        report = self.ledger.verify()
        checkpoints = (REPOSITORY_ROOT / "governance" / "CHECKPOINTS.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(report.head_hash, checkpoints)

    def test_project_ledger_is_exempt_from_line_ending_conversion(self):
        attributes = (REPOSITORY_ROOT / ".gitattributes").read_text(encoding="utf-8")
        self.assertIn("governance/events.jsonl -text", attributes.splitlines())


if __name__ == "__main__":
    unittest.main()
