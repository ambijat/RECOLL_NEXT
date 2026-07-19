#!/usr/bin/env python3
"""Runnable desktop companion for Recoll Next AI perspectives."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
from typing import Any, Dict, List, Optional, Sequence
from urllib.parse import unquote, urlparse
import webbrowser


VIEWS = ("answer", "summary", "timeline", "contradictions", "decisions", "actions")


class GUIContractError(Exception):
    """Raised when the CLI response cannot be presented safely."""


def build_command(
    script: Path,
    store: Path,
    query_text: str,
    operation: str,
    *,
    view: str = "answer",
) -> List[str]:
    if operation not in ("search", "ask"):
        raise GUIContractError("operation must be search or ask")
    if not query_text.strip():
        raise GUIContractError("enter a query first")
    command = [
        sys.executable,
        str(script),
        operation,
        "--store",
        str(store),
        "--json",
    ]
    if operation == "search":
        command.extend(("--timeout", "120", "--limit", "5"))
    else:
        if view not in VIEWS:
            raise GUIContractError("unsupported perspective")
        command.extend(
            (
                "--timeout",
                "600",
                "--evidence-limit",
                "2",
                "--view",
                view,
            )
        )
    command.append(query_text.strip())
    return command


def parse_response(raw_output: str) -> Dict[str, Any]:
    try:
        response = json.loads(raw_output)
    except json.JSONDecodeError as ex:
        raise GUIContractError("local AI returned invalid JSON") from ex
    if not isinstance(response, dict):
        raise GUIContractError("local AI response is not an object")
    if response.get("status") == "error":
        raise GUIContractError(str(response.get("error") or "local AI operation failed"))
    if response.get("status") not in ("ready", "answered"):
        raise GUIContractError("local AI returned an unsupported status")
    return response


def local_source_path(source: str) -> Optional[Path]:
    parsed = urlparse(source)
    if parsed.scheme != "file":
        return None
    decoded = unquote(parsed.path)
    if os.name == "nt" and len(decoded) >= 3 and decoded[0] == "/" and decoded[2] == ":":
        decoded = decoded[1:]
    return Path(decoded)


class AIPerspectiveApp:
    def __init__(self, root: Any, *, store: Path, query_text: str = ""):
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.ttk = ttk
        self.root = root
        self.root.title("Recoll Next — AI Perspective")
        self.root.geometry("1120x760")
        self.script = Path(__file__).with_name("recoll_ai.py")
        self.process: Optional[subprocess.Popen[str]] = None
        self.cancelled = False
        self.messages: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.evidence: Dict[str, Dict[str, Any]] = {}
        self.last_response: Optional[Dict[str, Any]] = None

        self.query_var = tk.StringVar(value=query_text)
        self.store_var = tk.StringVar(value=str(store))
        self.view_var = tk.StringVar(value="answer")
        self.status_var = tk.StringVar(value="Ready — local only")

        outer = ttk.Frame(root, padding=12)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(5, weight=2)
        outer.rowconfigure(7, weight=1)

        ttk.Label(outer, text="AI Perspective", font=("Segoe UI", 16, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w"
        )
        ttk.Label(
            outer,
            text="Local Ollama perspectives over traceable Recoll evidence.",
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 10))

        ttk.Label(outer, text="Query").grid(row=2, column=0, sticky="w")
        self.query_entry = ttk.Entry(outer, textvariable=self.query_var)
        self.query_entry.grid(row=2, column=1, columnspan=2, sticky="ew", padx=(8, 0))

        ttk.Label(outer, text="Knowledge scope").grid(row=3, column=0, sticky="w")
        self.store_entry = ttk.Entry(outer, textvariable=self.store_var)
        self.store_entry.grid(row=3, column=1, sticky="ew", padx=8, pady=6)
        ttk.Button(outer, text="Browse…", command=self.browse_store).grid(
            row=3, column=2, sticky="e"
        )

        controls = ttk.Frame(outer)
        controls.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(2, 10))
        self.search_button = ttk.Button(
            controls, text="Concept Search", command=lambda: self.start("search")
        )
        self.search_button.pack(side="left")
        self.ask_button = ttk.Button(
            controls, text="Ask AI", command=lambda: self.start("ask")
        )
        self.ask_button.pack(side="left", padx=6)
        ttk.Label(controls, text="Perspective").pack(side="left", padx=(14, 4))
        self.view_combo = ttk.Combobox(
            controls,
            textvariable=self.view_var,
            values=VIEWS,
            state="readonly",
            width=16,
        )
        self.view_combo.pack(side="left")
        self.cancel_button = ttk.Button(controls, text="Cancel", command=self.cancel)
        self.cancel_button.pack(side="right")
        self.export_button = ttk.Button(
            controls, text="Export Markdown…", command=self.export_markdown
        )
        self.export_button.pack(side="right", padx=6)

        answer_frame = ttk.LabelFrame(outer, text="Generated perspective")
        answer_frame.grid(row=5, column=0, columnspan=3, sticky="nsew")
        answer_frame.rowconfigure(0, weight=1)
        answer_frame.columnconfigure(0, weight=1)
        self.answer = tk.Text(answer_frame, wrap="word", padx=10, pady=10, height=12)
        self.answer.grid(row=0, column=0, sticky="nsew")
        answer_scroll = ttk.Scrollbar(answer_frame, command=self.answer.yview)
        answer_scroll.grid(row=0, column=1, sticky="ns")
        self.answer.configure(yscrollcommand=answer_scroll.set, state="disabled")

        self.progress = ttk.Progressbar(outer, mode="indeterminate")
        self.progress.grid(row=6, column=0, columnspan=3, sticky="ew", pady=8)

        evidence_frame = ttk.LabelFrame(
            outer, text="Evidence — double-click to open source"
        )
        evidence_frame.grid(row=7, column=0, columnspan=3, sticky="nsew")
        evidence_frame.rowconfigure(0, weight=1)
        evidence_frame.columnconfigure(0, weight=1)
        self.evidence_tree = ttk.Treeview(
            evidence_frame,
            columns=("title", "score", "source"),
            show="headings",
            selectmode="browse",
        )
        self.evidence_tree.heading("title", text="Document")
        self.evidence_tree.heading("score", text="Similarity")
        self.evidence_tree.heading("source", text="Source")
        self.evidence_tree.column("title", width=280)
        self.evidence_tree.column("score", width=90, anchor="center")
        self.evidence_tree.column("source", width=570)
        self.evidence_tree.grid(row=0, column=0, sticky="nsew")
        evidence_scroll = ttk.Scrollbar(evidence_frame, command=self.evidence_tree.yview)
        evidence_scroll.grid(row=0, column=1, sticky="ns")
        self.evidence_tree.configure(yscrollcommand=evidence_scroll.set)
        self.evidence_tree.bind("<Double-1>", self.open_selected_source)

        ttk.Label(outer, textvariable=self.status_var).grid(
            row=8, column=0, columnspan=3, sticky="w", pady=(8, 0)
        )
        self.set_busy(False)
        self.query_entry.focus_set()
        self.root.after(100, self.poll_messages)

    def browse_store(self) -> None:
        from tkinter import filedialog

        selected = filedialog.askopenfilename(
            title="Choose semantic knowledge store",
            initialfile=Path(self.store_var.get()).name,
            filetypes=(
                ("SQLite stores", "*.sqlite3 *.sqlite *.db"),
                ("All files", "*"),
            ),
        )
        if selected:
            self.store_var.set(selected)

    def start(self, operation: str) -> None:
        if self.process is not None:
            return
        store = Path(self.store_var.get().strip())
        if not store.is_file():
            self.show_error("Choose an existing semantic knowledge store.")
            return
        try:
            command = build_command(
                self.script,
                store,
                self.query_var.get(),
                operation,
                view=self.view_var.get(),
            )
        except GUIContractError as ex:
            self.show_error(str(ex))
            return

        self.clear_output()
        self.cancelled = False
        self.set_busy(True)
        self.status_var.set(
            "Retrieving semantic evidence…"
            if operation == "search"
            else "Retrieving evidence and generating with local Ollama…"
        )
        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        self.process = subprocess.Popen(
            command,
            cwd=Path(__file__).resolve().parents[2],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creation_flags,
        )
        threading.Thread(target=self.wait_for_process, daemon=True).start()

    def wait_for_process(self) -> None:
        assert self.process is not None
        stdout, stderr = self.process.communicate()
        code = self.process.returncode
        self.messages.put(("finished", (code, stdout, stderr)))

    def cancel(self) -> None:
        if self.process is None:
            return
        self.status_var.set("Cancelling local AI operation…")
        self.cancelled = True
        self.process.terminate()

    def poll_messages(self) -> None:
        try:
            while True:
                kind, payload = self.messages.get_nowait()
                if kind == "finished":
                    self.finish(*payload)
        except queue.Empty:
            pass
        self.root.after(100, self.poll_messages)

    def finish(self, return_code: int, stdout: str, stderr: str) -> None:
        self.process = None
        self.set_busy(False)
        if self.cancelled:
            self.status_var.set("Cancelled")
            self.cancelled = False
            return
        try:
            response = parse_response(stdout.strip())
            if return_code != 0:
                raise GUIContractError(
                    str(response.get("error") or "local AI operation failed")
                )
            self.render(response)
            self.status_var.set("Ready — evidence verified locally")
        except GUIContractError as ex:
            detail = str(ex)
            if stderr.strip():
                detail = stderr.strip()[-800:]
            self.show_error(detail)

    def render(self, response: Dict[str, Any]) -> None:
        self.last_response = response
        if response["status"] == "answered":
            answer = str(response.get("answer") or "")
            if response.get("insufficient_evidence"):
                answer += "\n\nEvidence status: insufficient."
            evidence = response.get("citations") or []
        else:
            evidence = response.get("results") or []
            answer = f"Conceptual evidence: {len(evidence)} segments found."
        self.set_answer(answer)
        for position, item in enumerate(evidence, start=1):
            if isinstance(item, dict):
                self.add_evidence(position, item)

    def add_evidence(self, position: int, item: Dict[str, Any]) -> None:
        title = str(item.get("title") or item.get("document_id") or "Untitled")
        path = str(item.get("path") or "")
        similarity = item.get("similarity")
        score = f"{float(similarity):.3f}" if isinstance(similarity, (int, float)) else ""
        identifier = self.evidence_tree.insert(
            "", "end", values=(f"[{position}] {title}", score, path)
        )
        self.evidence[identifier] = item

    def open_selected_source(self, _event: Any = None) -> None:
        selected = self.evidence_tree.selection()
        if not selected:
            return
        source = str(self.evidence.get(selected[0], {}).get("path") or "")
        if not source:
            return
        local = local_source_path(source)
        if local is not None and os.name == "nt":
            os.startfile(local)  # type: ignore[attr-defined]
        else:
            webbrowser.open(source)

    def export_markdown(self) -> None:
        from tkinter import filedialog

        if self.last_response is None:
            self.show_error("Run Concept Search or Ask AI before exporting.")
            return
        selected = filedialog.asksaveasfilename(
            title="Export AI perspective",
            defaultextension=".md",
            filetypes=(("Markdown", "*.md"), ("All files", "*")),
        )
        if not selected:
            return
        evidence = (
            self.last_response.get("citations")
            if self.last_response.get("status") == "answered"
            else self.last_response.get("results")
        ) or []
        lines = ["# Recoll Next AI Perspective", "", f"**Query:** {self.query_var.get()}", ""]
        if self.last_response.get("status") == "answered":
            lines.extend((str(self.last_response.get("answer") or ""), ""))
        lines.extend(("## Evidence", ""))
        for position, item in enumerate(evidence, start=1):
            lines.append(
                f"{position}. {item.get('title') or item.get('document_id') or 'Untitled'}"
            )
            lines.append(f"   - Source: {item.get('path') or ''}")
            lines.append(f"   - Segment: `{item.get('segment_id') or ''}`")
        Path(selected).write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.status_var.set(f"Exported: {selected}")

    def clear_output(self) -> None:
        self.last_response = None
        self.evidence.clear()
        self.evidence_tree.delete(*self.evidence_tree.get_children())
        self.set_answer("")

    def set_answer(self, value: str) -> None:
        self.answer.configure(state="normal")
        self.answer.delete("1.0", "end")
        self.answer.insert("1.0", value)
        self.answer.configure(state="disabled")

    def show_error(self, message: str) -> None:
        self.set_busy(False)
        self.status_var.set("Local AI operation failed")
        self.set_answer(f"Error: {message}")

    def set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        self.search_button.configure(state=state)
        self.ask_button.configure(state=state)
        self.store_entry.configure(state=state)
        self.query_entry.configure(state=state)
        self.view_combo.configure(state="disabled" if busy else "readonly")
        self.cancel_button.configure(state="normal" if busy else "disabled")
        if busy:
            self.progress.start(10)
        else:
            self.progress.stop()


def default_store(repository: Path) -> Path:
    academic = repository / ".local" / "booklibrandom-pdfs.sqlite3"
    return academic if academic.is_file() else repository / ".local" / "semantic.sqlite3"


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store")
    parser.add_argument("--query", default="")
    args = parser.parse_args(argv)

    import tkinter as tk

    repository = Path(__file__).resolve().parents[2]
    store = Path(args.store) if args.store else default_store(repository)
    root = tk.Tk()
    AIPerspectiveApp(root, store=store, query_text=args.query)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
