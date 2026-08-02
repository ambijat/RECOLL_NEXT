# Changelog

Recoll Next has not published a versioned release. The current `master` branch is a
source-development checkpoint, not a packaged binary release.

## Unreleased

### Implemented

- Local-only Ollama health, embedding, and cited-generation adapter.
- Deterministic segmentation and incremental SQLite semantic synchronization.
- Xapian-first Exact, Prismatic, and Conceptual retrieval with stale-evidence gates.
- Validated cited answers and provenance-gated Perspective Memory.
- Dependency-free Tk evidence workspace and separate semantic index builder.
- Native Qt AI Perspective dock source using the same JSON process boundary.
- Hash-chained project and runtime event ledgers.
- Offline-safe Python environment bootstrap and documented migration workflow.
- Self-contained root brochure and operator manual suitable for the repository landing
  page or static GitHub Pages publication.

### Still required for a binary release

- Compile and exercise the native Qt dock with a compatible toolchain.
- Produce and validate platform packaging and its component/license inventory.
- Complete a physical second-machine portability proof.
- Establish representative-corpus relevance and performance baselines.

Historical implementation checkpoints and their verified ledger heads are recorded in
[`governance/CHECKPOINTS.md`](governance/CHECKPOINTS.md). The active risks and next
milestone live in [`SESSION_START.md`](SESSION_START.md).
