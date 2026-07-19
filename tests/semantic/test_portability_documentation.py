from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
MARKDOWN_LINK = re.compile(r"\[[^]]+\]\(([^)]+)\)")


class PortabilityDocumentationTest(unittest.TestCase):
    def test_every_product_document_is_mandatory_session_reading(self):
        session = (ROOT / "SESSION_START.md").read_text(encoding="utf-8")
        documents = sorted((ROOT / "docs").glob("*.md"))

        missing = [
            document.name
            for document in documents
            if f"docs/{document.name}" not in session
        ]

        self.assertEqual([], missing)

    def test_agent_contract_enforces_portability_bootstrap(self):
        contract = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

        self.assertIn("Mandatory agent bootstrap", contract)
        self.assertIn("docs/PORTABILITY_CONTRACT.md", contract)
        self.assertIn("docs/AGENT_HANDOFF.md", contract)
        self.assertIn("every document listed under **Required reading**", contract)
        self.assertIn("No file edit", contract)

    def test_all_relative_markdown_links_resolve(self):
        sources = [ROOT / "README.md", ROOT / "AGENTS.md", ROOT / "SESSION_START.md"]
        sources.extend(sorted((ROOT / "docs").glob("*.md")))
        sources.extend(sorted((ROOT / "governance").glob("*.md")))
        broken = []

        for source in sources:
            text = source.read_text(encoding="utf-8")
            for raw_target in MARKDOWN_LINK.findall(text):
                target = raw_target.strip().strip("<>").split("#", 1)[0]
                if not target or "://" in target or target.startswith("mailto:"):
                    continue
                resolved = (source.parent / target).resolve()
                if not resolved.exists():
                    broken.append(f"{source.relative_to(ROOT)} -> {raw_target}")

        self.assertEqual([], broken)

    def test_verified_recoll_python_version_is_not_stale(self):
        # A previous handoff incorrectly recorded 3.13; the installed runtime is 3.12.4.
        session = (ROOT / "SESSION_START.md").read_text(encoding="utf-8")
        baseline = (ROOT / "docs" / "WORKSTATION_BASELINE.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Python 3.12.4", session)
        self.assertIn("3.12.4", baseline)
        self.assertNotIn("Python 3.13", session)


if __name__ == "__main__":
    unittest.main()
