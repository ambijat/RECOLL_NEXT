#!/usr/bin/env python3
"""Evidence-first Tk workspace for local Recoll Next perspectives."""

from __future__ import annotations

import os
from pathlib import Path
import queue
import subprocess
import threading
import time
from typing import Any, Dict, List, Optional, Sequence
import webbrowser

from recoll_ai_gui import (
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


class AIPerspectiveWorkspace:
    """Separate authoritative evidence discovery from optional interpretation."""

    def __init__(self, root: Any, *, store: Path, query_text: str = ""):
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.ttk = ttk
        self.root = root
        self.root.title("Recoll Next — AI Perspective")
        self.root.geometry("1280x900")
        self.script = Path(__file__).with_name("recoll_ai.py")
        self.process: Optional[subprocess.Popen[str]] = None
        self.cancelled = False
        self.messages: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.evidence: Dict[str, Dict[str, Any]] = {}
        self.evidence_order: List[str] = []
        self.last_response: Optional[Dict[str, Any]] = None
        self.search_response: Optional[Dict[str, Any]] = None
        self.search_signature: Optional[tuple[str, str, str]] = None
        self.active_operation = ""
        self.operation_started = 0.0
        self.operation_stage = ""
        self.operation_limit = 0
        self.runtime_expired = False

        self.query_var = tk.StringVar(value=query_text)
        self.store_var = tk.StringVar(value=str(store))
        self.view_var = tk.StringVar(value="answer")
        self.mode_var = tk.StringVar(value="prismatic")
        self.remember_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Ready — local only")
        self.scope_var = tk.StringVar()

        outer = ttk.Frame(root, padding=12)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(7, weight=1)
        outer.rowconfigure(9, weight=2)
        outer.rowconfigure(10, weight=1)

        ttk.Label(outer, text="AI Perspective", font=("Segoe UI", 16, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w"
        )
        ttk.Label(
            outer,
            text="Find traceable evidence first, then interpret only what you select.",
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 10))

        ttk.Label(outer, text="Query").grid(row=2, column=0, sticky="w")
        self.query_entry = ttk.Entry(outer, textvariable=self.query_var)
        self.query_entry.grid(row=2, column=1, columnspan=2, sticky="ew", padx=(8, 0))

        ttk.Label(outer, text="Semantic store").grid(row=3, column=0, sticky="w")
        self.store_entry = ttk.Entry(outer, textvariable=self.store_var)
        self.store_entry.grid(row=3, column=1, sticky="ew", padx=8, pady=6)
        ttk.Button(outer, text="Browse…", command=self.browse_store).grid(
            row=3, column=2, sticky="e"
        )
        ttk.Label(outer, textvariable=self.scope_var, foreground="#555555").grid(
            row=4, column=0, columnspan=3, sticky="w", pady=(0, 8)
        )

        find_frame = ttk.LabelFrame(outer, text="1. Find evidence", padding=8)
        find_frame.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        ttk.Label(find_frame, text="Retrieval mode").pack(side="left")
        self.mode_combo = ttk.Combobox(
            find_frame,
            textvariable=self.mode_var,
            values=("exact", "prismatic", "conceptual"),
            state="readonly",
            width=12,
        )
        self.mode_combo.pack(side="left", padx=6)
        self.search_button = ttk.Button(
            find_frame, text="Find Evidence", command=lambda: self.start("search")
        )
        self.search_button.pack(side="left")

        interpret_frame = ttk.LabelFrame(
            outer, text="2. Interpret visible evidence", padding=8
        )
        interpret_frame.grid(
            row=6, column=0, columnspan=3, sticky="ew", pady=(0, 8)
        )
        ttk.Label(interpret_frame, text="Perspective").pack(side="left")
        self.view_combo = ttk.Combobox(
            interpret_frame,
            textvariable=self.view_var,
            values=(
                "answer",
                "summary",
                "timeline",
                "contradictions",
                "decisions",
                "actions",
            ),
            state="readonly",
            width=16,
        )
        self.view_combo.pack(side="left", padx=6)
        self.ask_button = ttk.Button(
            interpret_frame,
            text="Interpret selected (or top 2)",
            command=lambda: self.start("ask"),
        )
        self.ask_button.pack(side="left")
        self.remember_check = ttk.Checkbutton(
            interpret_frame,
            text="Remember validated perspective locally",
            variable=self.remember_var,
        )
        self.remember_check.pack(side="left", padx=14)
        self.cancel_button = ttk.Button(
            interpret_frame, text="Cancel", command=self.cancel
        )
        self.cancel_button.pack(side="right")
        self.export_button = ttk.Button(
            interpret_frame, text="Export Markdown…", command=self.export_markdown
        )
        self.export_button.pack(side="right", padx=6)

        answer_frame = ttk.LabelFrame(outer, text="Generated perspective")
        answer_frame.grid(row=7, column=0, columnspan=3, sticky="nsew")
        answer_frame.rowconfigure(0, weight=1)
        answer_frame.columnconfigure(0, weight=1)
        self.answer = tk.Text(answer_frame, wrap="word", padx=10, pady=10, height=9)
        self.answer.grid(row=0, column=0, sticky="nsew")
        answer_scroll = ttk.Scrollbar(answer_frame, command=self.answer.yview)
        answer_scroll.grid(row=0, column=1, sticky="ns")
        self.answer.configure(yscrollcommand=answer_scroll.set, state="disabled")

        self.progress = ttk.Progressbar(outer, mode="indeterminate")
        self.progress.grid(row=8, column=0, columnspan=3, sticky="ew", pady=8)

        evidence_frame = ttk.LabelFrame(
            outer,
            text=(
                "Evidence — select rows for interpretation; double-click to open source"
            ),
        )
        evidence_frame.grid(row=9, column=0, columnspan=3, sticky="nsew")
        evidence_frame.rowconfigure(0, weight=1)
        evidence_frame.columnconfigure(0, weight=1)
        self.evidence_tree = ttk.Treeview(
            evidence_frame,
            columns=("rank", "title", "provenance", "score", "source"),
            show="headings",
            selectmode="extended",
        )
        for column, heading in (
            ("rank", "Final rank"),
            ("title", "Document"),
            ("provenance", "Found via"),
            ("score", "Ranking signal"),
            ("source", "Source"),
        ):
            self.evidence_tree.heading(column, text=heading)
        self.evidence_tree.column("rank", width=75, anchor="center", stretch=False)
        self.evidence_tree.column("title", width=300)
        self.evidence_tree.column("provenance", width=145, anchor="center")
        self.evidence_tree.column("score", width=135, anchor="center")
        self.evidence_tree.column("source", width=500)
        self.evidence_tree.grid(row=0, column=0, sticky="nsew")
        evidence_scroll = ttk.Scrollbar(evidence_frame, command=self.evidence_tree.yview)
        evidence_scroll.grid(row=0, column=1, sticky="ns")
        self.evidence_tree.configure(yscrollcommand=evidence_scroll.set)
        self.evidence_tree.bind("<Double-1>", self.open_selected_source)
        self.evidence_tree.bind("<<TreeviewSelect>>", self.show_selected_preview)

        preview_frame = ttk.LabelFrame(outer, text="Evidence preview")
        preview_frame.grid(row=10, column=0, columnspan=3, sticky="nsew", pady=(8, 0))
        preview_frame.rowconfigure(0, weight=1)
        preview_frame.columnconfigure(0, weight=1)
        self.preview = tk.Text(
            preview_frame, wrap="word", padx=10, pady=8, height=6, foreground="#333333"
        )
        self.preview.grid(row=0, column=0, sticky="nsew")
        preview_scroll = ttk.Scrollbar(preview_frame, command=self.preview.yview)
        preview_scroll.grid(row=0, column=1, sticky="ns")
        self.preview.configure(yscrollcommand=preview_scroll.set, state="disabled")

        ttk.Label(outer, textvariable=self.status_var).grid(
            row=11, column=0, columnspan=3, sticky="w", pady=(8, 0)
        )
        for variable in (self.query_var, self.store_var, self.mode_var):
            variable.trace_add("write", self.retrieval_changed)
        self.update_scope()
        self.set_busy(False)
        self.query_entry.focus_set()
        self.root.after(200, self.poll_messages)

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

    def current_signature(self) -> tuple[str, str, str]:
        return (
            self.query_var.get().strip(),
            str(Path(self.store_var.get().strip())),
            self.mode_var.get(),
        )

    def retrieval_changed(self, *_args: Any) -> None:
        self.update_scope()
        if (
            self.search_signature is not None
            and self.search_signature != self.current_signature()
        ):
            self.ask_button.configure(state="disabled")
            if self.process is None:
                self.status_var.set("Query or scope changed — find evidence again.")

    def update_scope(self) -> None:
        self.scope_var.set(
            scope_description(
                self.mode_var.get(), Path(self.store_var.get().strip() or ".")
            )
        )

    def start(self, operation: str) -> None:
        if self.process is not None:
            return
        store = Path(self.store_var.get().strip())
        mode = self.mode_var.get()
        if operation == "ask" and (
            self.search_response is None
            or self.search_signature != self.current_signature()
        ):
            self.show_error("Find evidence for the current query and mode first.")
            return
        if not (operation == "search" and mode == "exact") and not store.is_file():
            self.show_error("Choose an existing semantic knowledge store.")
            return

        selection: list[tuple[int, str]] = []
        if operation == "ask":
            selected = list(self.evidence_tree.selection()) or self.evidence_order[:2]
            selected.sort(key=self.evidence_order.index)
            for identifier in selected:
                item = self.evidence[identifier]
                selection.append(
                    (
                        self.evidence_order.index(identifier) + 1,
                        str(item.get("segment_id") or ""),
                    )
                )
        try:
            command = build_command(
                self.script,
                store,
                self.query_var.get(),
                operation,
                view=self.view_var.get(),
                mode=mode,
                remember=self.remember_var.get(),
                evidence_selection=selection,
            )
        except GUIContractError as ex:
            self.show_error(str(ex))
            return

        if operation == "search":
            self.clear_output()
        else:
            self.set_answer("")
        self.cancelled = False
        self.runtime_expired = False
        self.active_operation = operation
        self.operation_limit = 180 if operation == "search" else 660
        self.operation_started = time.monotonic()
        self.operation_stage = (
            f"Finding {mode.title()} evidence"
            if operation == "search"
            else (
                f"Interpreting {len(selection)} selected result(s) as "
                f"{self.view_var.get()}"
            )
        )
        self.set_busy(True)
        self.status_var.set(f"{self.operation_stage} — 0s, local only")
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
        process = self.process
        assert process is not None and process.stdout is not None and process.stderr is not None
        stderr_lines: list[str] = []

        def read_stderr() -> None:
            for line in process.stderr:
                progress = parse_progress_line(line.rstrip("\r\n"))
                if progress is not None:
                    self.messages.put(("progress", progress))
                else:
                    stderr_lines.append(line)

        reader = threading.Thread(target=read_stderr, daemon=True)
        reader.start()
        stdout = process.stdout.read()
        return_code = process.wait()
        reader.join(timeout=2)
        self.messages.put(("finished", (return_code, stdout, "".join(stderr_lines))))

    def cancel(self) -> None:
        if self.process is None:
            return
        self.status_var.set("Cancelling the owned local operation…")
        self.cancelled = True
        self.process.terminate()

    def poll_messages(self) -> None:
        try:
            while True:
                kind, payload = self.messages.get_nowait()
                if kind == "finished":
                    self.finish(*payload)
                elif kind == "progress":
                    self.show_progress(payload)
        except queue.Empty:
            pass
        if self.process is not None and not self.cancelled:
            elapsed = int(time.monotonic() - self.operation_started)
            if elapsed >= self.operation_limit:
                self.runtime_expired = True
                self.status_var.set("Stopping at the configured total runtime limit…")
                self.process.terminate()
            else:
                self.status_var.set(
                    f"{self.operation_stage} — {elapsed}s/{self.operation_limit}s, "
                    "local only; Cancel is available"
                )
        self.root.after(200, self.poll_messages)

    def show_progress(self, progress: Dict[str, Any]) -> None:
        labels = {
            "retrieving_evidence": "Retrieving and revalidating evidence",
            "generating_answer": "Generating a local cited answer",
            "validating_citations": "Validating generated citations",
            "completed": "Finalizing the validated answer",
        }
        self.operation_stage = labels.get(
            str(progress.get("stage") or ""), self.operation_stage
        )

    def finish(self, return_code: int, stdout: str, stderr: str) -> None:
        operation = self.active_operation
        elapsed = int(time.monotonic() - self.operation_started)
        self.process = None
        self.active_operation = ""
        self.set_busy(False)
        if self.runtime_expired:
            self.status_var.set(f"Stopped at total runtime limit after {elapsed}s")
            self.set_answer(
                "The local operation reached its total runtime limit. Retrieved evidence "
                "remains available; no unvalidated answer was displayed."
            )
            self.runtime_expired = False
            return
        if self.cancelled:
            self.status_var.set(f"Cancelled after {elapsed}s")
            self.cancelled = False
            return
        try:
            response = parse_response(stdout.strip())
            if return_code != 0:
                raise GUIContractError(
                    str(response.get("error") or "local AI operation failed")
                )
            if operation == "search":
                self.render_search(response)
            else:
                self.render_answer(response)
            self.status_var.set(f"Ready — evidence verified locally in {elapsed}s")
        except GUIContractError as ex:
            detail = str(ex)
            if stderr.strip():
                detail = stderr.strip()[-800:]
            self.show_error(detail)

    def render_search(self, response: Dict[str, Any]) -> None:
        self.last_response = response
        self.search_response = response
        self.search_signature = self.current_signature()
        evidence = response.get("results") or []
        mode = str(response.get("mode") or "conceptual")
        messages = [
            f"{mode.title()} retrieval found {len(evidence)} document(s).",
            scope_description(mode, Path(self.store_var.get().strip())),
        ]
        if response.get("degraded"):
            messages.append(
                "Semantic retrieval was unavailable; these are lexical fallback results."
            )
        stale = int(response.get("stale_rejected") or 0)
        if stale:
            messages.append(
                f"{stale} stale semantic candidate(s) were rejected against live Recoll."
            )
        if len(evidence) == 1:
            messages.append("Only one source was found; interpretation will be narrow.")
        self.set_answer("\n".join(messages))
        for position, item in enumerate(evidence, start=1):
            if isinstance(item, dict):
                self.add_evidence(position, item)
        if self.evidence_order:
            defaults = self.evidence_order[:2]
            self.evidence_tree.selection_set(*defaults)
            self.evidence_tree.focus(defaults[0])
            self.show_selected_preview()
        self.ask_button.configure(
            state="normal" if self.evidence_order else "disabled"
        )

    def add_evidence(self, position: int, item: Dict[str, Any]) -> None:
        title = clean_title(
            item.get("title") or item.get("document_id") or "Untitled"
        )
        path = str(item.get("path") or "")
        mode = str(item.get("retrieval_mode") or self.mode_var.get())
        identifier = self.evidence_tree.insert(
            "",
            "end",
            values=(
                f"#{position}",
                title,
                provenance_label(item),
                score_label(item, mode),
                path,
            ),
        )
        self.evidence[identifier] = item
        self.evidence_order.append(identifier)

    def render_answer(self, response: Dict[str, Any]) -> None:
        self.last_response = response
        answer = str(response.get("answer") or "")
        citations = [
            item for item in (response.get("citations") or []) if isinstance(item, dict)
        ]
        source_count = len({str(item.get("document_id")) for item in citations})
        header = (
            f"{str(response.get('view') or self.view_var.get()).title()} based on "
            f"{len(citations)} passage(s) across {source_count} source(s), retrieved "
            f"with {str(response.get('retrieval_mode') or self.mode_var.get()).title()}."
        )
        if response.get("insufficient_evidence"):
            header += " Evidence status: insufficient."
        header += (
            " Remembered locally."
            if response.get("remembered")
            else " Not added to Perspective Memory."
        )
        self.set_answer(header + "\n\n" + answer, citations=citations)
        cited_ids = {str(item.get("segment_id")) for item in citations}
        self.evidence_tree.tag_configure("cited", background="#e8f3ff")
        for identifier in self.evidence_order:
            item = self.evidence[identifier]
            tags = ("cited",) if str(item.get("segment_id")) in cited_ids else ()
            self.evidence_tree.item(identifier, tags=tags)

    def show_selected_preview(self, _event: Any = None) -> None:
        selected = self.evidence_tree.selection()
        if not selected:
            self.set_preview("")
            return
        item = self.evidence.get(selected[0], {})
        title = clean_title(item.get("title") or item.get("document_id") or "Untitled")
        mode = str(item.get("retrieval_mode") or self.mode_var.get())
        details = [
            title,
            (
                f"Why shown: {provenance_label(item) or mode.title()} — "
                f"{score_label(item, mode)}"
            ),
        ]
        if item.get("lexical_rank") is not None:
            details.append(f"Original lexical rank: #{item['lexical_rank']}")
        if item.get("semantic_rank") is not None:
            details.append(f"Original semantic rank: #{item['semantic_rank']}")
        details.extend(
            (
                f"Source: {item.get('path') or ''}",
                (
                    f"Offsets: {item.get('source_start', '')}–"
                    f"{item.get('source_end', '')}"
                ),
                "",
                str(item.get("text") or "No passage preview is available."),
            )
        )
        self.set_preview("\n".join(details))

    def open_selected_source(self, _event: Any = None) -> None:
        selected = self.evidence_tree.selection()
        if selected:
            self.open_item_source(self.evidence.get(selected[0], {}))

    def open_item_source(self, item: Dict[str, Any]) -> None:
        source = str(item.get("path") or "")
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
            self.show_error("Find evidence or interpret it before exporting.")
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
        lines = [
            "# Recoll Next AI Perspective",
            "",
            f"**Query:** {self.query_var.get()}",
            f"**Retrieval mode:** {self.mode_var.get()}",
            f"**Scope:** {scope_description(self.mode_var.get(), Path(self.store_var.get()))}",
            "",
        ]
        if self.last_response.get("status") == "answered":
            lines.extend((str(self.last_response.get("answer") or ""), ""))
        lines.extend(("## Evidence", ""))
        for position, item in enumerate(evidence, start=1):
            lines.append(
                f"{position}. {clean_title(item.get('title') or item.get('document_id') or 'Untitled')}"
            )
            lines.append(f"   - Source: {item.get('path') or ''}")
            lines.append(f"   - Segment: `{item.get('segment_id') or ''}`")
            lines.append(f"   - Found via: {provenance_label(item)}")
            lines.append(
                f"   - Ranking signal: {score_label(item, self.mode_var.get())}"
            )
        Path(selected).write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.status_var.set(f"Exported: {selected}")

    def clear_output(self) -> None:
        self.last_response = None
        self.search_response = None
        self.search_signature = None
        self.evidence.clear()
        self.evidence_order.clear()
        self.evidence_tree.delete(*self.evidence_tree.get_children())
        self.set_answer("")
        self.set_preview("")

    def set_answer(
        self, value: str, *, citations: Sequence[Dict[str, Any]] = ()
    ) -> None:
        self.answer.configure(state="normal")
        self.answer.delete("1.0", "end")
        self.answer.insert("1.0", value)
        if citations:
            self.answer.insert("end", "\n\nVerified sources:\n")
            for position, item in enumerate(citations, start=1):
                tag = f"source_{position}"
                title = clean_title(
                    item.get("title") or item.get("document_id") or "Untitled"
                )
                self.answer.insert("end", f"[{position}] {title}\n", (tag,))
                self.answer.tag_configure(tag, foreground="#005a9e", underline=True)
                self.answer.tag_bind(
                    tag,
                    "<Button-1>",
                    lambda _event, source=item: self.open_item_source(source),
                )
                self.answer.tag_bind(
                    tag,
                    "<Enter>",
                    lambda _event: self.answer.configure(cursor="hand2"),
                )
                self.answer.tag_bind(
                    tag,
                    "<Leave>",
                    lambda _event: self.answer.configure(cursor=""),
                )
        self.answer.configure(state="disabled")

    def set_preview(self, value: str) -> None:
        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", value)
        self.preview.configure(state="disabled")

    def show_error(self, message: str) -> None:
        self.set_busy(False)
        self.status_var.set("Local AI operation failed")
        self.set_answer(f"Error: {message}")

    def set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        self.search_button.configure(state=state)
        ask_ready = (
            not busy
            and self.search_response is not None
            and self.search_signature == self.current_signature()
            and bool(self.evidence_order)
        )
        self.ask_button.configure(state="normal" if ask_ready else "disabled")
        self.store_entry.configure(state=state)
        self.query_entry.configure(state=state)
        self.view_combo.configure(state="disabled" if busy else "readonly")
        self.mode_combo.configure(state="disabled" if busy else "readonly")
        self.remember_check.configure(state=state)
        self.cancel_button.configure(state="normal" if busy else "disabled")
        if busy:
            self.progress.grid()
            self.progress.start(10)
        else:
            self.progress.stop()
            self.progress.grid_remove()
