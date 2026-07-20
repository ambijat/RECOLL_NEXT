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
- The inherited Chroma implementation is retired; the active semantic subsystem uses
  a local SQLite sidecar and configurable loopback Ollama.
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
- `rclsem_hybrid.py` implements the Xapian-first search boundary: Exact preserves
  Recoll order without SQLite or Ollama, Prismatic concurrently fuses lexical and
  semantic candidates with configurable RRF, and Conceptual rejects evidence that
  cannot be resolved to the current Recoll revision. Both desktop surfaces expose
  all three modes and Prismatic reports lexical fallback when semantics fail.
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
- The Xapian-first protocol establishes the active Recoll database as lexical and
  document authority. The semantic database remains a disposable vector sidecar;
  the next retrieval refinement is removing transitional duplicated evidence fields
  after fully live hydration and measuring relevance on the representative corpus.
- `rclsem_perspectives.py` stores successfully validated cited answers as local,
  provenance-gated secondary memory. `ask` remembers by default with a
  `--no-remember` override, and `memory-search` retrieves current perspectives;
  memory reads now emit privacy-safe `search.memory.*` lifecycle events, and memories
  are not yet fed recursively into new answer prompts.
- The inherited Chroma entry points are explicit retirement stubs, and
  `src/semantic/initsemenv.py` creates a dependency-free environment on Windows or
  POSIX without downloading packages, models, or runtimes.
- The portability documentation suite defines source/data capsules, workstation
  reconstruction, configuration, build/test requirements, migration, operations,
  recovery, and mandatory cross-agent handoff. `AGENTS.md` requires every agent to
  read the complete `Required reading` set before mutation.
- A clean rebuild in an isolated local destination validated source, lexical, AI, and
  event fidelity at source commit `abc79e90`. It recreated Python without downloads,
  rebuilt a three-document Recoll/Xapian and semantic corpus, produced and rejected
  citations correctly, retrieved Perspective Memory, and launched the Tk companion.
  The private manifest is under `.local/portability-proof-20260720`.
- Inherited manuals, generated documentation, citation metadata, and legacy
  distribution packaging were removed to leave a rebuild skeleton.
- Existing local edits in `src/filters/cmdtalk.py` and
  `src/utils/cmdtalk.{cpp,h}` predate this foundation and must be preserved.

## Current milestone

Foundation and hardening:

1. Make the semantic subsystem deterministic, testable, and cross-platform.
2. Introduce the event ledger at subsystem boundaries.
3. Synchronize embeddings correctly for additions, updates, and deletions.
4. Measure and refine the implemented Exact/Prismatic/Conceptual retrieval slice on
   the representative private corpus, then remove transitional sidecar duplication.
5. Compile and package the implemented Recoll Qt AI Perspective dock; the runnable
   desktop companion is available for immediate validation.
6. Repeat the validated isolated clean-rebuild portability procedure on a second
   physical desktop and establish the native Qt build toolchain.

## Required reading

- [Documentation map](docs/README.md)
- [Portability contract](docs/PORTABILITY_CONTRACT.md)
- [Mandatory agent handoff](docs/AGENT_HANDOFF.md)
- [Verified workstation baseline](docs/WORKSTATION_BASELINE.md)
- [Development, build, and test guide](docs/DEVELOPMENT_AND_BUILD.md)
- [Configuration and storage reference](docs/CONFIGURATION_REFERENCE.md)
- [Local CLI and JSON API contract](docs/API_CONTRACT.md)
- [Desktop-to-desktop data migration](docs/DATA_MIGRATION.md)
- [Transfer manifest template](docs/TRANSFER_MANIFEST_TEMPLATE.md)
- [Local operations runbook](docs/OPERATIONS_RUNBOOK.md)
- [Component and responsibility catalog](docs/COMPONENT_CATALOG.md)
- [Security and privacy model](docs/SECURITY_AND_PRIVACY.md)
- [Provenance and licensing preservation](docs/PROVENANCE_AND_LICENSING.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Prismatic Search Charter](docs/PRISMATIC_SEARCH.md)
- [Xapian-first hybrid search protocol](docs/XAPIAN_FIRST_PROTOCOL.md)
- [Goal Fidelity Covenant](docs/GOAL_FIDELITY.md)
- [Local AI runtime](docs/LOCAL_AI_RUNTIME.md)
- [Semantic index foundation](docs/SEMANTIC_INDEX.md)
- [Semantic retrieval](docs/SEMANTIC_RETRIEVAL.md)
- [Local cited answers](docs/CITED_ANSWERS.md)
- [Perspective Memory](docs/PERSPECTIVE_MEMORY.md)
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

- An older native build configured with `ENABLE_SEMANTIC` still launches the retired
  `rclsem_talk.py` protocol and now fails explicitly. The supported native integration
  is the AI Perspective dock consuming `recoll_ai.py`; remove the older conditional
  path when the dock is compiled and validated.
- The repository `.venv` uses Python 3.14 while Recoll 1.43.5 ships bindings through
  Python 3.12.4. The automatic bundled-Python bridge is validated on this workstation;
  packaging still needs a general Windows installation-discovery contract.
- Exact cosine retrieval scans every stored segment. This is the reference-correct
  implementation, not the eventual large-corpus acceleration strategy.
- The first `gemma3:4b` cited answer took approximately 107 seconds on this machine;
  the GUI must expose progress and cancellation and must never block lexical search.
- The native Qt AI Perspective dock is implemented in source but cannot be compiled
  on this workstation until a matching Qt/C++ development SDK is installed. The
  Tk 8.6 desktop companion exercises the same customer workflow immediately.
- Same-workstation path isolation now passes Levels S/L/A/E, but cross-host and
  cross-OS portability remain unproven. The proof exposed and fixed overly broad Git
  bundles, missing `.venv` exclusion, and project-ledger line-ending conversion.

## Definition of the next stable checkpoint

A Windows-capable developer setup can index a small corpus, synchronize embeddings,
run lexical/semantic/hybrid searches, verify the event chain, and obtain an Ollama
answer with citations—all without network access after models and dependencies are
installed. The documented source and clean-rebuild data capsules can then reproduce
that checkpoint on a second desktop without relying on chat history or a Git remote.
