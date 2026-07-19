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
- Inherited manuals, generated documentation, citation metadata, and legacy
  distribution packaging were removed to leave a rebuild skeleton.
- Existing local edits in `src/filters/cmdtalk.py` and
  `src/utils/cmdtalk.{cpp,h}` predate this foundation and must be preserved.

## Current milestone

Foundation and hardening:

1. Make the semantic subsystem deterministic, testable, and cross-platform.
2. Introduce the event ledger at subsystem boundaries.
3. Synchronize embeddings correctly for additions, updates, and deletions.
4. Add hybrid lexical/semantic retrieval.
5. Add Ollama-generated answers whose claims link back to Recoll documents.

## Required reading

- [Architecture](docs/ARCHITECTURE.md)
- [Prismatic Search Charter](docs/PRISMATIC_SEARCH.md)
- [Goal Fidelity Covenant](docs/GOAL_FIDELITY.md)
- [Local AI runtime](docs/LOCAL_AI_RUNTIME.md)
- [Semantic index foundation](docs/SEMANTIC_INDEX.md)
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

- The inherited `rclsem_embed.py`/Chroma path still contains dropped-segment, stale
  deletion, and model-compatibility defects. It must be retired after the Recoll
  adapter and semantic query path move to the new SQLite foundation.
- Environment setup and worker launch assume Unix `bin/python3` paths.
- Semantic query failures are mostly surfaced only through logs.
- The new semantic store does not yet expose similarity retrieval or connect to the
  installed Recoll document inventory.

## Definition of the next stable checkpoint

A Windows-capable developer setup can index a small corpus, synchronize embeddings,
run lexical/semantic/hybrid searches, verify the event chain, and obtain an Ollama
answer with citations—all without network access after models and dependencies are
installed.
