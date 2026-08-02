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
    clean_title,
    local_source_path,
    parse_progress_line,
    parse_response,
    provenance_label,
    scope_description,
    score_label,
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
        self.assertEqual("prismatic", command[command.index("--mode") + 1])
        self.assertEqual("5", command[command.index("--limit") + 1])
        self.assertEqual("energy policy", command[-1])

    def test_exact_search_command_has_no_semantic_store_dependency(self):
        command = build_command(
            Path("recoll_ai.py"),
            Path("missing.sqlite3"),
            "title:policy",
            "search",
            mode="exact",
        )
        self.assertNotIn("--store", command)
        self.assertEqual("exact", command[command.index("--mode") + 1])

    def test_ask_command_uses_safe_workstation_limits(self):
        command = build_command(
            Path("recoll_ai.py"),
            Path("semantic.sqlite3"),
            "research decisions",
            "ask",
            view="decisions",
            mode="prismatic",
            evidence_selection=((2, "segment-2"),),
        )
        self.assertEqual("2", command[command.index("--evidence-limit") + 1])
        self.assertEqual("600", command[command.index("--timeout") + 1])
        self.assertEqual("660", command[command.index("--max-runtime") + 1])
        self.assertEqual("decisions", command[command.index("--view") + 1])
        self.assertEqual("prismatic", command[command.index("--mode") + 1])
        self.assertEqual("2", command[command.index("--evidence-rank") + 1])
        self.assertEqual(
            "segment-2", command[command.index("--expected-segment-id") + 1]
        )
        self.assertIn("--no-remember", command)

    def test_ask_command_can_explicitly_enable_local_memory(self):
        command = build_command(
            Path("recoll_ai.py"),
            Path("semantic.sqlite3"),
            "research decisions",
            "ask",
            remember=True,
        )
        self.assertNotIn("--no-remember", command)

    def test_sync_command_uses_json_and_default_scope(self):
        command = build_command(
            Path("recoll_ai.py"), Path("semantic.sqlite3"), "", "sync"
        )
        self.assertEqual("sync", command[2])
        self.assertIn("--json", command)
        self.assertEqual("mime:*", command[command.index("--query") + 1])
        self.assertNotIn("--keep-missing", command)

    def test_sync_command_supports_custom_scope_and_keep_missing(self):
        command = build_command(
            Path("recoll_ai.py"),
            Path("semantic.sqlite3"),
            "",
            "sync",
            scope_query="dir:F:/Eurasianism2",
            keep_missing=True,
            sync_timeout=300,
            sync_batch_size=2,
            sync_max_runtime=1200,
            confdir="profiles/practice",
        )
        self.assertEqual(
            "dir:F:/Eurasianism2", command[command.index("--query") + 1]
        )
        self.assertIn("--keep-missing", command)
        self.assertEqual("300", command[command.index("--timeout") + 1])
        self.assertEqual("2", command[command.index("--batch-size") + 1])
        self.assertEqual("1200", command[command.index("--max-runtime") + 1])
        self.assertEqual("profiles/practice", command[command.index("--confdir") + 1])
        self.assertIn("--progress", command)

    def test_progress_parser_accepts_only_prefixed_structured_stage(self):
        self.assertEqual(
            {"stage": "batch_completed", "batch_index": 2},
            parse_progress_line(
                'RECOLL_PROGRESS {"stage":"batch_completed","batch_index":2}'
            ),
        )
        self.assertIsNone(parse_progress_line("ordinary diagnostic"))
        self.assertIsNone(parse_progress_line("RECOLL_PROGRESS not-json"))

    def test_sync_command_rejects_empty_scope(self):
        with self.assertRaises(GUIContractError):
            build_command(
                Path("recoll_ai.py"),
                Path("semantic.sqlite3"),
                "",
                "sync",
                scope_query="   ",
            )

    def test_invalid_operation_and_empty_query_are_rejected(self):
        with self.assertRaises(GUIContractError):
            build_command(Path("ai.py"), Path("store.db"), "query", "backup")
        with self.assertRaises(GUIContractError):
            build_command(Path("ai.py"), Path("store.db"), " ", "search")

    def test_response_parser_accepts_only_gui_contract_statuses(self):
        response = parse_response(
            json.dumps({"status": "ready", "result_count": 0, "results": []})
        )
        self.assertEqual("ready", response["status"])
        sync_response = parse_response(
            json.dumps({"status": "synchronized", "segments_embedded": 0})
        )
        self.assertEqual("synchronized", sync_response["status"])
        with self.assertRaisesRegex(GUIContractError, "denied"):
            parse_response(json.dumps({"status": "error", "error": "denied"}))
        with self.assertRaises(GUIContractError):
            parse_response(json.dumps({"status": "unsupported"}))

    def test_file_urls_resolve_for_clickable_evidence(self):
        path = local_source_path("file:///F:/BOOKLIBRANDOM/paper.pdf")
        expected = (
            Path("F:/BOOKLIBRANDOM/paper.pdf")
            if os.name == "nt"
            else Path("/F:/BOOKLIBRANDOM/paper.pdf")
        )
        self.assertEqual(expected, path)
        self.assertIsNone(local_source_path("https://example.invalid/paper"))

    def test_presentation_helpers_explain_scope_provenance_and_scores(self):
        self.assertEqual("“Quoted” title", clean_title("&ldquo;Quoted&rdquo;  title"))
        item = {
            "provenance": ["lexical", "semantic"],
            "fusion_score": 0.029,
            "lexical_rank": 4,
        }
        self.assertEqual("Lexical + Semantic", provenance_label(item))
        self.assertEqual("Fusion 0.029", score_label(item, "prismatic"))
        self.assertEqual("Rank #4", score_label(item, "exact"))
        self.assertEqual(
            "Lexical fallback #4",
            score_label({"lexical_rank": 4}, "prismatic"),
        )
        self.assertIn(
            "active Recoll profile",
            scope_description("exact", Path("semantic.sqlite3")),
        )
        self.assertIn(
            "semantic.sqlite3",
            scope_description("conceptual", Path("semantic.sqlite3")),
        )


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
        workspace = (
            REPOSITORY / "src" / "semantic" / "recoll_ai_workspace.py"
        ).read_text(encoding="utf-8")
        index_builder = (
            REPOSITORY / "src" / "semantic" / "recoll_ai_index_builder.py"
        ).read_text(encoding="utf-8")
        for build_file in (cmake, qmake):
            self.assertIn("aiperspective_w.cpp", build_file)
            self.assertIn("aiperspective_w.h", build_file)
        self.assertIn("addDockWidget(Qt::RightDockWidgetArea", main)
        self.assertIn("resultsReady", main)
        self.assertIn("sSearch->currentText()", main)
        self.assertIn("QProcess", dock)
        self.assertIn('"--json"', dock)
        self.assertIn('"--mode"', dock)
        self.assertIn('"--no-remember"', dock)
        self.assertIn('m_modeCombo->addItem(tr("Exact"), "exact")', dock)
        self.assertIn('m_modeCombo->addItem(tr("Prismatic"), "prismatic")', dock)
        self.assertIn('m_modeCombo->addItem(tr("Conceptual"), "conceptual")', dock)
        self.assertIn("openSourceRequested", dock)
        self.assertIn("Interpret visible evidence", workspace)
        self.assertIn("Remember validated perspective locally", workspace)
        self.assertIn("Found via", workspace)
        self.assertIn("Evidence preview", workspace)
        self.assertNotIn("Build knowledge", workspace)
        self.assertIn("Semantic Indexing", index_builder)
        self.assertIn("Run Semantic Indexing", index_builder)
        self.assertIn('"sync"', index_builder)

    def test_obsolete_native_semantic_worker_route_is_removed(self):
        active_files = [
            REPOSITORY / "src" / "meson.build",
            REPOSITORY / "src" / "meson_options.txt",
            REPOSITORY / "src" / "qtgui" / "main.cpp",
            REPOSITORY / "src" / "qtgui" / "recoll.h",
            REPOSITORY / "src" / "qtgui" / "rclm_menus.cpp",
            REPOSITORY / "src" / "qtgui" / "rclmain_w.cpp",
            REPOSITORY / "src" / "qtgui" / "ssearch_w.cpp",
            REPOSITORY / "src" / "qtgui" / "ssearch_w.h",
            REPOSITORY / "src" / "qtgui" / "xmltosd.cpp",
        ]
        active_text = "\n".join(
            path.read_text(encoding="utf-8") for path in active_files
        )
        for retired_symbol in (
            "ENABLE_SEMANTIC",
            "DocSequenceSem",
            "docseqsem",
            "SST_SEM",
            "semantic_enabled",
            "rclsem_talk.py",
        ):
            self.assertNotIn(retired_symbol, active_text)
        self.assertFalse((REPOSITORY / "src" / "query" / "docseqsem.cpp").exists())
        self.assertFalse((REPOSITORY / "src" / "query" / "docseqsem.h").exists())

        tombstone = (
            REPOSITORY / "src" / "semantic" / "rclsem_talk.py"
        ).read_text(encoding="utf-8")
        self.assertIn("retired", tombstone.lower())
        self.assertIn("RETIREMENT_MESSAGE", tombstone)
        retirement_message = (
            REPOSITORY / "src" / "semantic" / "rclsem_common.py"
        ).read_text(encoding="utf-8")
        self.assertIn("recoll_ai.py", retirement_message)


if __name__ == "__main__":
    unittest.main()
