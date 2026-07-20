# AI Perspective workspace

## Visible deliverable

The AI Perspective workspace is the customer-facing surface for the Polaroid/Prism
model. It leaves ordinary Recoll results intact and adds optional local semantic
search and cited Ollama perspectives.

Two presentation paths consume the same backend contract:

- `src/qtgui/aiperspective_w.{h,cpp}` is a right-side `QDockWidget` integrated into
  Recoll's `RclMain`.
- `src/semantic/recoll_ai_gui.py` is a dependency-free Tk 8.6 companion that runs
  immediately from the repository virtual environment.

Launch the working companion from the repository root:

```powershell
python src\semantic\recoll_ai_gui.py `
  --store .local\booklibrandom-pdfs.sqlite3
```

## Customer controls

The workspace provides:

- a query copied from the completed Recoll search in the native dock, or entered
  directly in the companion;
- a browsable semantic knowledge-scope store;
- **Concept Search** for evidence cards;
- **Ask AI** for answer, summary, timeline, contradiction, decision, and action views;
- indeterminate progress that never blocks the ordinary Recoll result list;
- **Cancel** for the current local child process;
- evidence rows showing title, similarity, and source;
- double-click source opening;
- Markdown export in the runnable companion.

The GUI deliberately does not run generation automatically. The user chooses when to
apply an Ollama perspective.

## Process boundary

Both interfaces invoke `recoll_ai.py` asynchronously and require `--json`. Search is
bounded to five evidence results. Generation is bounded to the two highest-ranked
segments and uses a 600-second workstation timeout established by live testing.

Arguments are passed as an argument vector, never through shell interpolation. The
question and evidence travel only between local processes and loopback Ollama. Runtime
ledgers retain digests and identifiers rather than private query or document text.

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
- An absent semantic store produces an actionable scope-selection message.
- Empty evidence produces the backend's explicit insufficient-evidence response.
- Generated citations remain subject to the cited-answer validator before display.

## Current validation

The semantic and GUI-contract suite has 70 passing tests. Tests cover command
construction, workstation limits, response-status validation, clickable file URLs,
native build-file inclusion, main-window query handoff, asynchronous `QProcess` use,
the retired Chroma boundary, cross-platform offline bootstrap, audited memory reads,
and the established retrieval, answer, privacy, and ledger invariants.

The desktop companion was launched successfully on Tk 8.6 against the academic PDF
semantic store. Native Qt source compilation remains pending because this workstation
has the Recoll runtime libraries but no Qt/C++ development SDK or build executable.

Successful cited Ask operations now also create provenance-gated Perspective Memory
unless `--no-remember` is supplied. The present GUI does not yet expose a memory
toggle or memory-search panel; packaging must make background retention visible and
manageable before release.
