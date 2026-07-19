from pathlib import Path
import json
import os
import sys
import unittest


REPOSITORY = Path(__file__).resolve().parents[2]
SEMANTIC_SOURCE = REPOSITORY / "src" / "semantic"
sys.path.insert(0, str(SEMANTIC_SOURCE))

from recoll_ai_gui import (  # noqa: E402
    GUIContractError,
    build_command,
    local_source_path,
    parse_response,
)


class DesktopCompanionContractTest(unittest.TestCase):
    def test_search_command_uses_json_and_bounded_results(self):
        command = build_command(
            Path("recoll_ai.py"),
            Path("semantic.sqlite3"),
            "energy policy",
            "search",
        )
        self.assertIn("--json", command)
        self.assertEqual("search", command[2])
        self.assertEqual("5", command[command.index("--limit") + 1])
        self.assertEqual("energy policy", command[-1])

    def test_ask_command_uses_safe_workstation_limits(self):
        command = build_command(
            Path("recoll_ai.py"),
            Path("semantic.sqlite3"),
            "research decisions",
            "ask",
            view="decisions",
        )
        self.assertEqual("2", command[command.index("--evidence-limit") + 1])
        self.assertEqual("600", command[command.index("--timeout") + 1])
        self.assertEqual("decisions", command[command.index("--view") + 1])

    def test_invalid_operation_and_empty_query_are_rejected(self):
        with self.assertRaises(GUIContractError):
            build_command(Path("ai.py"), Path("store.db"), "query", "sync")
        with self.assertRaises(GUIContractError):
            build_command(Path("ai.py"), Path("store.db"), " ", "search")

    def test_response_parser_accepts_only_gui_contract_statuses(self):
        response = parse_response(
            json.dumps({"status": "ready", "result_count": 0, "results": []})
        )
        self.assertEqual("ready", response["status"])
        with self.assertRaisesRegex(GUIContractError, "denied"):
            parse_response(json.dumps({"status": "error", "error": "denied"}))
        with self.assertRaises(GUIContractError):
            parse_response(json.dumps({"status": "synchronized"}))

    def test_file_urls_resolve_for_clickable_evidence(self):
        path = local_source_path("file:///F:/BOOKLIBRANDOM/paper.pdf")
        expected = (
            Path("F:/BOOKLIBRANDOM/paper.pdf")
            if os.name == "nt"
            else Path("/F:/BOOKLIBRANDOM/paper.pdf")
        )
        self.assertEqual(expected, path)
        self.assertIsNone(local_source_path("https://example.invalid/paper"))


class NativeQtIntegrationContractTest(unittest.TestCase):
    def test_native_dock_is_built_and_wired_into_main_window(self):
        cmake = (REPOSITORY / "src" / "qtgui" / "CMakeLists.txt").read_text(
            encoding="utf-8"
        )
        qmake = (REPOSITORY / "src" / "qtgui" / "recoll.pro.in").read_text(
            encoding="utf-8"
        )
        main = (REPOSITORY / "src" / "qtgui" / "rclmain_w.cpp").read_text(
            encoding="utf-8"
        )
        dock = (REPOSITORY / "src" / "qtgui" / "aiperspective_w.cpp").read_text(
            encoding="utf-8"
        )
        for build_file in (cmake, qmake):
            self.assertIn("aiperspective_w.cpp", build_file)
            self.assertIn("aiperspective_w.h", build_file)
        self.assertIn("addDockWidget(Qt::RightDockWidgetArea", main)
        self.assertIn("resultsReady", main)
        self.assertIn("sSearch->currentText()", main)
        self.assertIn("QProcess", dock)
        self.assertIn('"--json"', dock)
        self.assertIn("openSourceRequested", dock)


if __name__ == "__main__":
    unittest.main()
