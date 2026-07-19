# Recoll Next — session start

Read this file at the beginning of every work session.

## Mission

Build a private, local-first knowledge system on the Recoll indexing engine. Recoll
provides extraction, indexing, metadata, and lexical retrieval. Ollama provides local
embeddings and generation. The product adds semantic retrieval, cited answers, and a
tamper-evident history of system activity.

This clone is independent. The configured Git remote is historical metadata only and
must not be contacted.

## Current state

- Recoll's C++/Qt application and Python bindings are present.
- An experimental Ollama + ChromaDB semantic search exists in `src/semantic`.
- The semantic prototype is Unix-oriented and is not yet reliable on Windows.
- A standalone hash-chained event ledger foundation lives in
  `src/semantic/rclsem_ledger.py`.
- The first executable AI artifact is `src/semantic/recoll_ai.py doctor`, backed by the
  dependency-free local-only adapter in `src/semantic/rclsem_ollama.py`.
- Deterministic segmentation, model-versioned SQLite storage, and incremental
  synchronization live in `rclsem_segments.py`, `rclsem_store.py`, and
  `rclsem_sync.py`; the live `embeddinggemma` path has been validated at 768
  dimensions.
- `rclsem_recoll.py` exposes Recoll's `rcludi` inventory lazily, and
  `rclsem_retrieve.py` performs deterministic exact cosine retrieval with source
  metadata and offsets. `recoll_ai.py` exposes both as `sync` and `search`.
- On Windows, a Python-ABI mismatch falls back automatically to
  `rclsem_recoll_bridge.py` running under the Python runtime bundled with the local
  Recoll installation. Document transfer remains local over a private pipe.
- `rclsem_answer.py` implements bounded local synthesis with `gemma3:4b`. The `ask`
  command validates every generated citation against retrieved segment IDs and
  supports answer, summary, timeline, contradiction, decision, and action views.
- `aiperspective_w.{h,cpp}` wires a native AI Perspective dock into `RclMain`, while
  `recoll_ai_gui.py` provides an immediately runnable dependency-free desktop
  companion. Both consume the same asynchronous `search --json` and `ask --json`
  contracts and expose evidence, cancellation, and source opening.
- The Xapian-first protocol establishes the active Recoll database as the lexical and
  document authority. The semantic database is a disposable vector sidecar and the
  next retrieval artifact is bounded Xapian candidate generation plus Ollama
  reranking.
- Inherited manuals, generated documentation, citation metadata, and legacy
  distribution packaging were removed to leave a rebuild skeleton.
- Existing local edits in `src/filters/cmdtalk.py` and
  `src/utils/cmdtalk.{cpp,h}` predate this foundation and must be preserved.

## Current milestone

Foundation and hardening:

1. Make the semantic subsystem deterministic, testable, and cross-platform.
2. Introduce the event ledger at subsystem boundaries.
3. Synchronize embeddings correctly for additions, updates, and deletions.
4. Add hybrid lexical/semantic retrieval; semantic-only retrieval is complete.
5. Compile and package the implemented Recoll Qt AI Perspective dock; the runnable
   desktop companion is available for immediate validation.

## Required reading

- [Architecture](docs/ARCHITECTURE.md)
- [Prismatic Search Charter](docs/PRISMATIC_SEARCH.md)
- [Xapian-first hybrid search protocol](docs/XAPIAN_FIRST_PROTOCOL.md)
- [Goal Fidelity Covenant](docs/GOAL_FIDELITY.md)
- [Local AI runtime](docs/LOCAL_AI_RUNTIME.md)
- [Semantic index foundation](docs/SEMANTIC_INDEX.md)
- [Semantic retrieval](docs/SEMANTIC_RETRIEVAL.md)
- [Local cited answers](docs/CITED_ANSWERS.md)
- [AI Perspective workspace](docs/AI_WORKSPACE.md)
- [Event ledger specification](docs/EVENT_LEDGER.md)
- [Project governance ledger](governance/README.md)
- [Implementation roadmap](docs/ROADMAP.md)

Inherited product documentation is intentionally unavailable. Add new documentation
only when it describes the rebuilt product or records legally required provenance.

## Working rules

- No remote Git or cloud-model operations.
- Do not log full document content, prompts containing private content, credentials,
  tokens, or environment dumps.
- Treat the ledger as evidence, not as a queue or source database.
- Test every feature against the Goal Fidelity Covenant and record major decisions in
  `governance/events.jsonl`.
- Every answer must retain document and segment identifiers so the UI can display its
  evidence.
- Run focused tests after every change and document any test that cannot run locally.

## Known immediate defects

- The inherited `rclsem_embed.py`/Chroma path is superseded but not yet retired;
  callers must move to `recoll_ai.py sync` and `recoll_ai.py search`.
- Environment setup and worker launch assume Unix `bin/python3` paths.
- The repository `.venv` uses Python 3.14 while Recoll 1.43.5 ships bindings through
  Python 3.13. The automatic bundled-Python bridge is validated on this workstation;
  packaging still needs a general Windows installation-discovery contract.
- Exact cosine retrieval scans every stored segment. This is the reference-correct
  implementation, not the eventual large-corpus acceleration strategy.
- The first `gemma3:4b` cited answer took approximately 107 seconds on this machine;
  the GUI must expose progress and cancellation and must never block lexical search.
- The native Qt AI Perspective dock is implemented in source but cannot be compiled
  on this workstation until a matching Qt/C++ development SDK is installed. The
  Tk 8.6 desktop companion exercises the same customer workflow immediately.

## Definition of the next stable checkpoint

A Windows-capable developer setup can index a small corpus, synchronize embeddings,
run lexical/semantic/hybrid searches, verify the event chain, and obtain an Ollama
answer with citations—all without network access after models and dependencies are
installed.
