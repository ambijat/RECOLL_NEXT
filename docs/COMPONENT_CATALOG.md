# Component and responsibility catalog

## End-to-end flow

```text
Original files
  -> Recoll extractors and metadata filters
  -> Xapian lexical index selected by Recoll profile
  -> Recoll Python inventory/query adapter
  -> deterministic source-preserving segments
  -> local Ollama embeddings
  -> SQLite semantic namespace
  -> Xapian-first Exact / Prismatic RRF / Conceptual retrieval
  -> bounded local Ollama generation
  -> citation validator
  -> optional Perspective Memory
  -> Tk companion / native Qt AI dock

Cross-cutting: runtime JSONL ledger and versioned project governance chain
```

## Active semantic modules

| Module | Responsibility | Inputs | Outputs/failures |
| --- | --- | --- | --- |
| `recoll_ai.py` | CLI and JSON process boundary | Commands, paths, models, queries | Reports or typed sanitized errors |
| `rclsem_ollama.py` | Dependency-free local HTTP adapter and policy | Loopback endpoint, model, bounded requests | Model inventory, embeddings, chat; typed policy/connection/API/protocol errors |
| `rclsem_segments.py` | Deterministic segmentation | `SourceDocument`, target/overlap settings | Stable revision and segment identities with offsets |
| `rclsem_store.py` | Semantic SQLite ownership | Namespaces, documents, segments, vectors | Atomic records, exact iteration, compatibility errors |
| `rclsem_sync.py` | Incremental synchronization | Recoll inventory, segmenter, embedder | Add/update/unchanged/delete report and runtime events |
| `rclsem_recoll.py` | Authoritative inventory, bounded lexical query, and live-resolution adapter | Recoll profile/query/`rcludi` | Ordered `SourceDocument` records; automatic Windows ABI bridge |
| `rclsem_recoll_bridge.py` | Matching-ABI child process | Profile/query or private-stdin identities under bundled Python | Private JSON Lines document stream |
| `rclsem_retrieve.py` | Reference semantic ranker | Query embedding and stored vectors | Deterministic cosine-ranked `EvidenceResult` records |
| `rclsem_hybrid.py` | Xapian-first retrieval coordinator | Lexical documents, semantic evidence, mode and RRF policy | Provenance-bearing, stale-gated Exact/Prismatic/Conceptual reports |
| `rclsem_answer.py` | Bounded cited generation | Query, view, primary evidence, chat model | Validated `CitedAnswer` or explicit rejection/decline |
| `rclsem_perspectives.py` | Secondary interpretation memory and audited retrieval | Validated cited answer, query, and embedding | Deduplicated memory, stale-gated retrieval, and `search.memory.*` events |
| `rclsem_events.py` | Component-to-ledger adapter | Typed event and minimized payload | Hash-chained runtime append |
| `rclsem_ledger.py` | Append-only SHA-256 chain | Canonical bounded JSON events | Verified JSONL chain and head hash |
| `recoll_ai_gui.py` | Immediately runnable Tk workspace | Query, store, selected view | Async search/ask, evidence, source open, export |

## Native presentation modules

| Module | Responsibility | Status |
| --- | --- | --- |
| `src/qtgui/aiperspective_w.h/.cpp` | Right-side AI dock, async child process, controls, evidence | Implemented in source; not compiled on baseline machine |
| `src/qtgui/rclmain_w.h/.cpp` | Main-window ownership, View toggle, Recoll query handoff, source opening | Implemented in source; static contract tested |
| `src/qtgui/CMakeLists.txt` | Native CMake source inclusion | Updated |
| `src/qtgui/recoll.pro.in` | qmake source inclusion | Updated |

The installed Recoll executable is an external runtime build and does not reflect
uncompiled source changes.

## Retired semantic modules

| Module | Historical role | Current rule |
| --- | --- | --- |
| `rclsem_common.py` | Chroma/Ollama helper and configuration | Retirement tombstone; fails with migration guidance |
| `rclsem_embed.py` | Chroma population | Retirement tombstone; use `recoll_ai.py sync` |
| `rclsem_query.py` | Chroma semantic query | Retirement tombstone; use `recoll_ai.py search` |
| `rclsem_talk.py` | Older native semantic worker | Retirement tombstone for an older `ENABLE_SEMANTIC` build |
| `cmdtalkplugin.py`, `slicelist.py`, `rclsem_segment.py` | Superseded helper lineage | No active callers; retained pending native-path removal review |
| `initsemenv.py` | Dependency-free environment creation | Active cross-platform, offline-safe bootstrap |

The tombstones preserve a bounded compatibility failure while the older conditional
native path is still present. They contain no Chroma implementation or dependency.

## Inherited Recoll engine areas

The repository retains Recoll's acquisition, filters, index, query, database, common
utilities, native UI, Python binding, platform integration, and test source. This
project does not recreate an inherited user manual. The governing product boundary
is that these components remain the base engine and are changed only through small,
testable integration points.

Material source areas include:

- `src/filters`, `src/internfile` — format extraction and normalization;
- `src/index`, `src/rcldb`, `src/query` — indexing, Xapian database, and query logic;
- `src/common`, `src/utils`, `src/xaposix` — shared platform/runtime utilities;
- `src/qtgui` — native desktop UI;
- `src/python/recoll` — Python binding source;
- `src/windows`, `src/kde`, `src/desktop` — platform integration;
- `src/sampleconf` — inherited configuration examples;
- `src/testmains` and `tests` — inherited and rebuilt-product verification.

## Data stores

| Store | Writer | Reader | Rebuild source |
| --- | --- | --- | --- |
| Original corpus | User/application outside Recoll Next | Recoll extractors | Original backup |
| Xapian `dbdir` | Recoll indexer | Recoll query/API | Corpus plus profile |
| Semantic SQLite tables | Semantic synchronizer | Semantic search/answer/memory validator | Recoll inventory plus embedding model |
| Perspective tables | Successful cited `ask` | `memory-search` | Not automatically reproducible; derived session knowledge |
| Runtime ledger | Semantic components | Ledger verifier/operator | Append-only evidence; not reconstructed silently |
| Project ledger | Project governance workflow | Agents/operator/tests | Versioned append-only record |

Perspective Memory is derived but may carry useful intellectual work. Treat it as a
selected private migration capsule even though it is never primary documentary truth.

## Test-to-contract map

| Test module | Principal contract |
| --- | --- |
| `test_ollama_client.py` | Loopback privacy, model inventory, response validation |
| `test_semantic_sync.py` | Determinism, dimensions, atomic incremental lifecycle |
| `test_semantic_retrieval.py` | Recoll identity bridge and exact cosine evidence |
| `test_hybrid_retrieval.py` | Xapian order, RRF, stale rejection, outage fallback, query privacy, store-free Exact |
| `test_cited_answer.py` | Bounded prompt, supported views, citation rejection |
| `test_perspective_memory.py` | Deduplication, namespace dimensions, stale provenance |
| `test_ai_perspective_gui.py` | GUI process arguments, cancellation/source contracts, native wiring |
| `test_event_ledger.py` | Canonical chain, tamper detection, concurrency/locking |
| `test_project_governance.py` | Genesis goal, allowed events, checkpointed head |

## Implemented versus planned

Implemented: local doctor, Recoll inventory/query bridge, deterministic semantic sync,
exact cosine retrieval, Xapian-first Exact/Prismatic/Conceptual search with RRF and
live revision gates, cited answer views, Perspective Memory indexing/search,
runtime/project ledgers, Tk GUI, and native dock source.

Planned/incomplete: semantic-schema de-duplication after live hydration, full-corpus
vector acceleration, memory-assisted generation with
strict primary/secondary labels, memory management UI, native Windows build/package,
schema migration tools, signed ledger checkpoints, and second-machine portability
validation.
