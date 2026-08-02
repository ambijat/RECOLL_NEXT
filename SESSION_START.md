# Recoll Next — session start

Read this file at the beginning of every work session.

## Mission

Build a private, local-first knowledge system on the Recoll indexing engine. Recoll
provides extraction, indexing, metadata, and lexical retrieval. Ollama provides local
embeddings and generation. The product adds semantic retrieval, cited answers, and a
tamper-evident history of system activity.

This clone is independent. The inherited Recoll remote is historical metadata only.
Remote access is denied by default, with a narrow exception for an exact destination
and operation explicitly authorized by the user after the local publication gate.

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
  Structured generation now constrains citation values to the exact supplied segment
  allowlist before the independent fail-closed validator runs.
- `aiperspective_w.{h,cpp}` wires a native AI Perspective dock into `RclMain`, while
  `recoll_ai_gui.py` provides an immediately runnable dependency-free desktop
  companion. Both consume the same asynchronous `search --json` and `ask --json`
  contracts and expose evidence, cancellation, and source opening.
- The standalone semantic index builder now exposes request timeout, embedding batch
  size, Recoll profile, and total-runtime controls; streams privacy-safe document/batch
  progress; and terminates its owned child at the configured limit. CLI cancellation
  exits cleanly with code 130, while answer progress distinguishes retrieval,
  generation, and citation validation under a separate total-runtime budget. The
  semantic suite has 98 passing tests.
- The obsolete native `ENABLE_SEMANTIC`/`DocSequenceSem` route has been removed from
  the build and Qt simple-search surface. The supported AI Perspective dock remains
  independent, while Python retirement tombstones continue to guide older installed
  binaries without keeping the dead route active.
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
- Public-source preparation now includes a current root README, GPL-2.0-or-later
  contribution notice, contribution and security policies, changelog, brochure,
  quick start, and a contract-safe publication checklist. Private corpus/runtime/model
  artifacts remain excluded. The user has authorized initial publication of the
  selected product branch to `https://github.com/ambijat/RECOLL_NEXT.git`; this does
  not authorize fetch, pull, force-push, ref deletion, or any other remote.
- Local source checkpoint `af461ea4` passed Python compilation, all 98 semantic tests,
  governance verification, product-document link validation, whitespace checks, and
  representative ignore-policy checks. Governance event 33 records the milestone at
  head `8633a8279073e00c72b89c032d665a313100b783e2e8e84cf191f05b3d6a263c`.
- Governance event 34 records the user-directed default-deny publication exception for
  `https://github.com/ambijat/RECOLL_NEXT.git` at head
  `1bfa4ac9df7a6deed930f469e09a96db5bc5b1c12df18d41bf1c2b1bd3816c27`.
- Initial source publication succeeded to the public GitHub repository
  `https://github.com/ambijat/RECOLL_NEXT` with only `master` at `f406abfd` pushed.
  Governance event 35 records the outcome at head
  `8ff9560f8d78030c420776c756332671f0241ae21aa93e475e9f5a32b09c03cc`.
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
7. Preserve a locally verified, public-source-ready checkpoint and publish only the
   explicitly authorized product branch to the exact governed destination.

## Required reading

- [Next-session restart capsule](RESUME_NEXT_SESSION.md)
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
- [Source publication checklist](docs/PUBLICATION_CHECKLIST.md)

Inherited product documentation is intentionally unavailable. Add new documentation
only when it describes the rebuilt product or records legally required provenance.

## Working rules

- No Git remote operation without an exact user-authorized destination and action;
  no cloud-model operations.
- Do not log full document content, prompts containing private content, credentials,
  tokens, or environment dumps.
- Treat the ledger as evidence, not as a queue or source database.
- Test every feature against the Goal Fidelity Covenant and record major decisions in
  `governance/events.jsonl`.
- Every answer must retain document and segment identifiers so the UI can display its
  evidence.
- Run focused tests after every change and document any test that cannot run locally.

## Known immediate defects

- The repository `.venv` uses Python 3.14 while Recoll 1.43.5 ships bindings through
  Python 3.12.4. The automatic bundled-Python bridge is validated on this workstation;
  packaging still needs a general Windows installation-discovery contract.
- The active workstation Recoll profile currently resolves repository documents from
  the predecessor `recoll` working tree rather than this `recoll_next` tree. Use a
  deliberately scoped profile or rebuild before treating repository search as a
  current relevance baseline.
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
