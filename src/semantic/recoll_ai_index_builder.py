#!/usr/bin/env python3
"""Standalone Tk tool for semantic indexing of a Recoll Next knowledge store.

Kept deliberately separate from recoll_ai_workspace.py: semantic indexing is an
occasional, slow, higher-stakes maintenance operation, not part of the everyday
search/interpret flow. It never rebuilds or touches Recoll's own index.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import queue
import subprocess
import threading
import time
from typing import Any, Dict, Optional

from recoll_ai_gui import GUIContractError, build_command, parse_progress_line, parse_response


class IndexBuilderApp:
    """Run semantic indexing for one SQLite store from a Recoll query scope."""

    def __init__(self, root: Any, *, store: Path, scope_query: str = "mime:*", confdir: str = "", request_timeout: int = 120, batch_size: int = 4, max_runtime: int = 900):
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.ttk = ttk
        self.root = root
        self.root.title("Recoll Next — Semantic Indexing")
        self.root.geometry("900x680")
        self.script = Path(__file__).with_name("recoll_ai.py")
        self.process: Optional[subprocess.Popen[str]] = None
        self.cancelled = False
        self.runtime_expired = False
        self.messages: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.operation_started = 0.0

        self.store_var = tk.StringVar(value=str(store))
        self.scope_var = tk.StringVar(value=scope_query)
        self.confdir_var = tk.StringVar(value=confdir)
        self.timeout_var = tk.StringVar(value=str(request_timeout))
        self.batch_size_var = tk.StringVar(value=str(batch_size))
        self.max_runtime_var = tk.StringVar(value=str(max_runtime))
        self.keep_missing_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="Ready — local only")

        outer = ttk.Frame(root, padding=12)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(1, weight=1)

        ttk.Label(outer, text="Semantic Indexing", font=("Segoe UI", 16, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w"
        )
        ttk.Label(
            outer,
            text=(
                "Builds and repairs the separate semantic store the AI Perspective's "
                "Prismatic/Conceptual modes read from. This does not rebuild or touch "
                "Recoll's own index, and does not modify your source files."
            ),
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 10))

        ttk.Label(outer, text="Semantic store").grid(row=2, column=0, sticky="w")
        self.store_entry = ttk.Entry(outer, textvariable=self.store_var)
        self.store_entry.grid(row=2, column=1, sticky="ew", padx=8, pady=6)
        ttk.Button(outer, text="Browse…", command=self.browse_store).grid(
            row=2, column=2, sticky="e"
        )

        ttk.Label(outer, text="Recoll scope").grid(row=3, column=0, sticky="w")
        self.scope_entry = ttk.Entry(outer, textvariable=self.scope_var)
        self.scope_entry.grid(row=3, column=1, sticky="ew", padx=8, pady=6)
        ttk.Label(
            outer,
            text='e.g. "mime:*" for everything Recoll indexes, or "dir:BOOKLIBRANDOM mime:application/pdf" for one folder',
            foreground="#555555",
        ).grid(row=4, column=0, columnspan=3, sticky="w", pady=(0, 8))

        ttk.Label(outer, text="Recoll profile").grid(row=5, column=0, sticky="w")
        self.confdir_entry = ttk.Entry(outer, textvariable=self.confdir_var)
        self.confdir_entry.grid(row=5, column=1, sticky="ew", padx=8, pady=6)
        ttk.Label(outer, text="blank = Recoll default").grid(row=5, column=2, sticky="w")

        limits = ttk.Frame(outer)
        limits.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(2, 8))
        ttk.Label(limits, text="Request timeout (s)").pack(side="left")
        self.timeout_entry = ttk.Entry(limits, textvariable=self.timeout_var, width=7)
        self.timeout_entry.pack(side="left", padx=(6, 16))
        ttk.Label(limits, text="Batch size").pack(side="left")
        self.batch_entry = ttk.Entry(limits, textvariable=self.batch_size_var, width=6)
        self.batch_entry.pack(side="left", padx=(6, 16))
        ttk.Label(limits, text="Total limit (s)").pack(side="left")
        self.max_runtime_entry = ttk.Entry(limits, textvariable=self.max_runtime_var, width=8)
        self.max_runtime_entry.pack(side="left", padx=6)

        controls = ttk.Frame(outer)
        controls.grid(row=7, column=0, columnspan=3, sticky="new", pady=(0, 8))
        self.keep_missing_check = ttk.Checkbutton(
            controls,
            text="Keep documents missing from this scope (never delete)",
            variable=self.keep_missing_var,
        )
        self.keep_missing_check.pack(side="left")
        self.sync_button = ttk.Button(
            controls, text="Run Semantic Indexing", command=self.start
        )
        self.sync_button.pack(side="right")
        self.cancel_button = ttk.Button(
            controls, text="Cancel", command=self.cancel
        )
        self.cancel_button.pack(side="right", padx=6)

        self.progress = ttk.Progressbar(outer, mode="indeterminate")
        self.progress.grid(row=8, column=0, columnspan=3, sticky="ew", pady=8)

        report_frame = ttk.LabelFrame(outer, text="Semantic indexing report")
        report_frame.grid(row=9, column=0, columnspan=3, sticky="nsew")
        report_frame.rowconfigure(0, weight=1)
        report_frame.columnconfigure(0, weight=1)
        outer.rowconfigure(9, weight=1)
        self.report = tk.Text(report_frame, wrap="word", padx=10, pady=10, height=14)
        self.report.grid(row=0, column=0, sticky="nsew")
        report_scroll = ttk.Scrollbar(report_frame, command=self.report.yview)
        report_scroll.grid(row=0, column=1, sticky="ns")
        self.report.configure(yscrollcommand=report_scroll.set, state="disabled")

        ttk.Label(outer, textvariable=self.status_var).grid(
            row=10, column=0, columnspan=3, sticky="w", pady=(8, 0)
        )
        self.set_busy(False)
        self.root.after(200, self.poll_messages)

    def browse_store(self) -> None:
        from tkinter import filedialog

        selected = filedialog.asksaveasfilename(
            title="Choose or create a semantic knowledge store",
            initialfile=Path(self.store_var.get()).name,
            defaultextension=".sqlite3",
            filetypes=(
                ("SQLite stores", "*.sqlite3 *.sqlite *.db"),
                ("All files", "*"),
            ),
        )
        if selected:
            self.store_var.set(selected)

    def start(self) -> None:
        if self.process is not None:
            return
        store = Path(self.store_var.get().strip())
        if not store.name:
            self.show_error("Choose a semantic knowledge store path first.")
            return
        try:
            request_timeout = int(self.timeout_var.get())
            batch_size = int(self.batch_size_var.get())
            max_runtime = int(self.max_runtime_var.get())
            if min(request_timeout, batch_size, max_runtime) <= 0:
                raise ValueError
        except ValueError:
            self.show_error("Timeout, batch size, and total limit must be positive integers.")
            return
        try:
            command = build_command(
                self.script,
                store,
                "",
                "sync",
                scope_query=self.scope_var.get(),
                keep_missing=self.keep_missing_var.get(),
                sync_timeout=request_timeout,
                sync_batch_size=batch_size,
                sync_max_runtime=max_runtime,
                confdir=self.confdir_var.get(),
            )
        except GUIContractError as ex:
            self.show_error(str(ex))
            return

        self.set_report("")
        self.cancelled = False
        self.runtime_expired = False
        self.operation_started = time.monotonic()
        self.set_busy(True)
        self.status_var.set(
            f"Synchronizing '{self.scope_var.get().strip()}' into {store.name} — 0s"
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
            max_runtime = int(self.max_runtime_var.get())
            if elapsed >= max_runtime:
                self.runtime_expired = True
                self.status_var.set("Stopping at the configured total runtime limit…")
                self.process.terminate()
        self.root.after(200, self.poll_messages)

    def finish(self, return_code: int, stdout: str, stderr: str) -> None:
        elapsed = int(time.monotonic() - self.operation_started)
        self.process = None
        self.set_busy(False)
        if self.runtime_expired:
            self.status_var.set(f"Stopped at total runtime limit after {elapsed}s")
            self.set_report(
                "Indexing stopped at the configured total runtime limit. Completed "
                "documents remain valid; an unfinished document was not partially installed."
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
            self.render(response)
            self.status_var.set(
                f"Ready — semantic indexing verified locally in {elapsed}s"
            )
        except GUIContractError as ex:
            detail = str(ex)
            if stderr.strip():
                detail = stderr.strip()[-800:]
            self.show_error(detail)

    def show_progress(self, progress: Dict[str, Any]) -> None:
        elapsed = int(time.monotonic() - self.operation_started)
        stage = str(progress.get("stage") or "working").replace("_", " ").title()
        document = progress.get("document_index")
        batch = progress.get("batch_index")
        batches = progress.get("batches_total")
        segments = progress.get("segments_embedded", 0)
        detail = stage
        if document is not None:
            detail += f" — document {document}"
        if batch is not None:
            detail += f", batch {batch}/{batches}"
        self.status_var.set(f"{detail}, {segments} segment(s) embedded — {elapsed}s")

    def render(self, response: Dict[str, Any]) -> None:
        lines = [
            f"Synchronized scope '{self.scope_var.get().strip()}' into "
            f"{Path(self.store_var.get().strip()).name}.",
            "",
            f"Documents added:     {response.get('documents_added', 0)}",
            f"Documents updated:   {response.get('documents_updated', 0)}",
            f"Documents unchanged: {response.get('documents_unchanged', 0)}",
            f"Documents deleted:   {response.get('documents_deleted', 0)}",
            f"Segments embedded:   {response.get('segments_embedded', 0)}",
            "",
            "Open the AI Perspective app and Find Evidence again to see the "
            "updated knowledge store.",
        ]
        self.set_report("\n".join(lines))

    def set_report(self, value: str) -> None:
        self.report.configure(state="normal")
        self.report.delete("1.0", "end")
        self.report.insert("1.0", value)
        self.report.configure(state="disabled")

    def show_error(self, message: str) -> None:
        self.set_busy(False)
        self.status_var.set("Semantic indexing failed")
        self.set_report(f"Error: {message}")

    def set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        self.sync_button.configure(state=state)
        self.store_entry.configure(state=state)
        self.scope_entry.configure(state=state)
        self.confdir_entry.configure(state=state)
        self.timeout_entry.configure(state=state)
        self.batch_entry.configure(state=state)
        self.max_runtime_entry.configure(state=state)
        self.keep_missing_check.configure(state=state)
        self.cancel_button.configure(state="normal" if busy else "disabled")
        if busy:
            self.progress.start(10)
        else:
            self.progress.stop()


def default_store(repository: Path) -> Path:
    academic = repository / ".local" / "booklibrandom-pdfs.sqlite3"
    return academic if academic.is_file() else repository / ".local" / "semantic.sqlite3"


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store")
    parser.add_argument("--query", default="mime:*")
    parser.add_argument("--confdir", default="")
    parser.add_argument("--timeout", default=120, type=int)
    parser.add_argument("--batch-size", default=4, type=int)
    parser.add_argument("--max-runtime", default=900, type=int)
    args = parser.parse_args(argv)

    import tkinter as tk

    repository = Path(__file__).resolve().parents[2]
    store = Path(args.store) if args.store else default_store(repository)
    root = tk.Tk()
    IndexBuilderApp(
        root,
        store=store,
        scope_query=args.query,
        confdir=args.confdir,
        request_timeout=args.timeout,
        batch_size=args.batch_size,
        max_runtime=args.max_runtime,
    )
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
