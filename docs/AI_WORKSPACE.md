# AI Perspective workspace

## Visible deliverable

The AI Perspective workspace is the customer-facing surface for the Polaroid/Prism
model. It leaves ordinary Recoll results intact and adds optional local semantic
search and cited Ollama perspectives.

Two presentation paths consume the same backend contract:

- `src/qtgui/aiperspective_w.{h,cpp}` is a right-side `QDockWidget` integrated into
  Recoll's `RclMain`.
- `src/semantic/recoll_ai_workspace.py` is a dependency-free Tk 8.6 companion that runs
  immediately from the repository virtual environment. `src/semantic/recoll_ai_gui.py`
  holds the command-construction and response-parsing contract shared by both Tk apps
  and is also the launcher `main()` for the workspace.

Semantic indexing (the `sync` operation) is a separate, deliberately isolated tool,
`src/semantic/recoll_ai_index_builder.py`: an occasional, slower, higher-stakes
maintenance action, not part of the everyday search/interpret flow. It never rebuilds
or touches Recoll's own lexical index.

Launch either working companion from the repository root, or double-click
`AI-Perspective.bat` / `Rebuild-Index.bat` at the repository root (they run the same
scripts with `pythonw.exe`, no console window):

```powershell
python src\semantic\recoll_ai_gui.py `
  --store .local\booklibrandom-pdfs.sqlite3
python src\semantic\recoll_ai_index_builder.py `
  --store .local\booklibrandom-pdfs.sqlite3
```

## Customer controls

The workspace enforces a two-step "find evidence, then interpret" flow so
interpretation is never applied to evidence the user has not seen:

- a query copied from the completed Recoll search in the native dock, or entered
  directly in the companion;
- a browsable semantic knowledge-scope store;
- **1. Find evidence** — Exact, Prismatic, or Conceptual retrieval mode;
- **2. Interpret visible evidence** — answer, summary, timeline, contradiction,
  decision, or action view, applied to the rows selected in the evidence list (or the
  top two if none are selected); each selected row is revalidated by rank and segment
  identity against a fresh authoritative search before generation, so the CLI rejects
  the request if the underlying evidence changed since it was found;
- **Remember validated perspective locally**, an explicit checkbox controlling whether
  a successful cited answer is written to Perspective Memory (off by default);
- privacy-safe stage progress for retrieval, local generation, and citation validation
  that never blocks the ordinary Recoll result list;
- **Cancel** for the current local child process;
- evidence rows showing final rank, title, provenance ("found via"), channel-appropriate
  score/rank, and source, plus an evidence preview pane and cited-row highlighting;
- double-click source opening;
- Markdown export in the runnable companion.

The GUI deliberately does not run generation automatically. The user chooses when to
apply an Ollama perspective.

Semantic indexing has its own controls in `recoll_ai_index_builder.py`, kept out of the
search/interpret workspace: a store path, Recoll scope query and profile, per-request
timeout, embedding batch size, total runtime limit, document/batch progress, and a "Keep documents
missing from this scope (never delete)" checkbox that is **checked by default** so a
narrow or mistaken scope query cannot silently delete semantic-store documents outside
that scope — see `docs/OPERATIONS_RUNBOOK.md` for scope-query guidance.

## Process boundary

Both interfaces invoke `recoll_ai.py` asynchronously and require `--json`. Search is
bounded to five evidence results. Generation is bounded to the two highest-ranked
segments, uses a 600-second request timeout, and has a 660-second workspace deadline.
The
native dock remains a single-step search-then-ask against the selected mode and always
passes `--no-remember`; it does not yet use the Tk workspace's separate find/interpret
steps or the rank/segment-identity evidence-selection contract.

Arguments are passed as an argument vector, never through shell interpolation. The
question and evidence travel only between local processes and loopback Ollama. Runtime
ledgers retain digests and identifiers rather than private query or document text.
Structured progress travels on stderr with the `RECOLL_PROGRESS` prefix; stdout remains
exactly one JSON response for API compatibility. Progress contains stages and counts,
not document text, titles, paths, questions, or answers.

The native dock resolves development paths from the repository working directory.
Packaged or nonstandard layouts can configure:

```text
RECOLL_AI_PYTHON
RECOLL_AI_SCRIPT
RECOLL_AI_WORKDIR
RECOLL_AI_STORE
```

## Failure isolation

- Recoll lexical search never waits for the AI process.
- Starting or parsing failure appears inside the perspective panel.
- Cancellation terminates only the AI child process.
- CLI `Ctrl+C` returns exit code 130 with a bounded cancellation message instead of a
  traceback. The index builder terminates its child at the configured total runtime limit.
- An absent semantic store disables Prismatic, Conceptual, and Ask while Exact
  continues through Recoll without Ollama.
- Empty evidence produces the backend's explicit insufficient-evidence response.
- Generated citations remain subject to the cited-answer validator before display.

## Current validation

The semantic and GUI-contract suite has 98 passing tests. Tests cover command
construction, workstation limits, response-status validation, clickable file URLs,
native build-file inclusion, main-window query handoff, asynchronous `QProcess` use,
the retired Chroma boundary, removal of the obsolete native semantic worker route,
cross-platform offline bootstrap, audited memory reads, hybrid rank/provenance and
outage behavior, evidence-selection revalidation, and the established answer, privacy,
and ledger invariants.

The desktop companion was launched successfully on Tk 8.6 against the academic PDF
semantic store. Native Qt source compilation remains pending because this workstation
has the Recoll runtime libraries but no Qt/C++ development SDK or build executable.

Successful cited Ask operations now also create provenance-gated Perspective Memory
unless `--no-remember` is supplied. The Tk workspace exposes this as the explicit
"Remember validated perspective locally" checkbox (see Customer controls); a
memory-search panel is not yet built into either GUI, so `memory-search` remains a
CLI-only operation. The native dock still always passes `--no-remember` and has no
memory toggle.
