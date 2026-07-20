from pathlib import Path
import sys
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SEMANTIC_SOURCE = REPOSITORY_ROOT / "src" / "semantic"
sys.path.insert(0, str(SEMANTIC_SOURCE))

from initsemenv import venv_interpreter  # noqa: E402
from rclsem_common import (  # noqa: E402
    LegacySemanticPathRetired,
    RETIREMENT_MESSAGE,
    common_init,
)


class EnvironmentBootstrapTest(unittest.TestCase):
    def test_resolves_platform_specific_environment_interpreters(self):
        root = Path("environment")
        self.assertEqual(
            root / "Scripts" / "python.exe", venv_interpreter(root, "nt")
        )
        self.assertEqual(root / "bin" / "python", venv_interpreter(root, "posix"))

    def test_bootstrap_and_active_modules_have_no_chroma_import(self):
        for path in SEMANTIC_SOURCE.glob("*.py"):
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("import chromadb", source, path.name)

    def test_recreated_environment_is_ignored_by_source_capsules(self):
        ignore_rules = (REPOSITORY_ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(".venv/", ignore_rules.splitlines())

    def test_retired_entry_point_fails_with_supported_commands(self):
        with self.assertRaisesRegex(LegacySemanticPathRetired, "recoll_ai.py sync"):
            common_init()
        self.assertIn("and 'search'", RETIREMENT_MESSAGE)


if __name__ == "__main__":
    unittest.main()
