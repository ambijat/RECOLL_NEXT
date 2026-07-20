# Implementation roadmap

## Phase 0 — repository operating foundation

- Maintain the session briefing and architectural decisions.
- Add and test the local event-ledger primitive.
- Preserve inherited changes and prohibit accidental remote operations.
- Maintain the mandatory portability and agent-handoff documentation suite.

Exit: a new session can orient itself from `SESSION_START.md`, and a ledger can append
and verify events while detecting mutation.

## Phase 1 — semantic subsystem hardening

Implemented foundation: the local-only Ollama adapter, deterministic versioned
segmenter, model-versioned SQLite store, incremental synchronization, stale deletion,
dimension validation, privacy-safe synchronization events, lazy Recoll inventory
adapter, Windows bundled-Python compatibility bridge, and deterministic exact cosine
retrieval.

- Separate configuration, Ollama client, segmentation, vector-store, and Recoll
  adapters. (Implemented for the command-line vertical slice.)
- Support Windows and Unix virtual environments and worker launch paths.
- Fix dropped segments and add deterministic segmentation tests.
- Store source revision, model, dimensions, and segmentation version as metadata.
- Synchronize additions, updates, and deletions idempotently.
- Add health checks and actionable GUI errors.
- Emit `index.semantic.*` and `search.semantic.*` events. (`model.embedding.*`
  remains for worker-level instrumentation.)
- Retire the inherited Chroma implementation, provide an offline-safe cross-platform
  environment bootstrap, and emit privacy-safe `search.memory.*` events. (Implemented.)

Exit: repeated synchronization produces the same semantic index, changed files update
correctly, deleted files disappear, and failures are diagnosed.

## Phase 2 — hybrid retrieval

- Implement the duties and acceptance criteria in the Prismatic Search Charter.
- Define a shared evidence result contract.
- Retrieve lexical and semantic candidates concurrently.
- Normalize/rank with reciprocal-rank fusion initially; keep the algorithm pluggable.
- Preserve Recoll filters and expose result provenance and scores.
- Add corpus-based relevance regression tests.

Exit: hybrid search is never materially worse than either source on the reference
corpus and remains usable without Ollama.

## Phase 3 — local cited answers

- Add a configurable Ollama generation adapter with timeouts. (Implemented;
  cancellation remains for the GUI worker.)
- Construct bounded context from deduplicated evidence. (Implemented for semantic
  evidence.)
- Require citations in a machine-readable response contract. (Implemented.)
- Validate cited identifiers against supplied context. (Implemented.)
- Display answer, uncertainty, and navigable Recoll sources in Qt.
- Provide a runnable desktop companion while the native Qt build toolchain is being
  established. (Implemented.)
- Emit privacy-minimized `model.generation.*` and `answer.*` events.

Exit: answers cite real indexed segments, gracefully decline unsupported questions,
and never require cloud services.

## Phase 4 — integrity and operations

- Document source/data capsules, workstation reconstruction, configuration, build,
  migration, security, routine operations, and agent handoff. (Implemented; an
  isolated same-workstation clean rebuild passed Levels S/L/A/E, while a physical
  second-machine validation remains.)
- Add ledger head checkpoints and optional local asymmetric signatures.
- Add retention, export, redaction-by-tombstone policy, and recovery tooling.
- Add migration/versioning for semantic stores and ledger schemas.
- Package an offline-capable Windows installation and model readiness checks.

Exit: administrators can verify provenance, migrate safely, and recover derived stores
without losing original content or lexical search.

## Phase 5 — product refinement

- Saved knowledge workspaces, reusable searches, and answer notebooks.
- User feedback signals for local relevance tuning.
- Performance budgets, background scheduling, accessibility, and localization.
- Stable automation API with the same evidence and audit contracts as the GUI.
