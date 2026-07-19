# Xapian-first hybrid search protocol

## Status and purpose

This is the normative retrieval protocol for Recoll Next. It prevents the local AI
layer from recreating capabilities already supplied by Recoll and Xapian, while
preserving the dense-vector data required for semantic retrieval.

The protocol applies to indexing, synchronization, search, answer generation, and
the desktop presentation layer.

## Governing boundary

Recoll and its Xapian database are the authoritative document inventory, extraction
pipeline, metadata catalogue, and lexical search engine. Ollama is an optional local
enrichment layer. A semantic store may retain derived vectors, but it must never
become an independent source of document truth.

For the current workstation, the active Recoll profile declares:

```text
dbdir = D:/recoll_windex
```

That path is profile configuration, not a product constant. Every component must
discover the active database through the selected Recoll configuration directory.

## Ownership of data

| Information | Authoritative owner | Semantic sidecar policy |
| --- | --- | --- |
| Original document body | Source file | Never authoritative |
| Extracted searchable text | Recoll/Xapian | Fetch when evidence is presented |
| Title, path, MIME type, dates, and fields | Recoll/Xapian | Do not duplicate except as an explicitly bounded cache |
| Document identity | Recoll `rcludi` | Store only as a foreign identity |
| Terms, positions, phrases, and lexical scores | Xapian | Do not recreate |
| Segment identity and source offsets | Semantic sidecar | Store as derived coordinates |
| Source revision fingerprint | Semantic sidecar | Store for invalidation only |
| Embedding model, dimensions, and version | Semantic sidecar | Store as a namespace contract |
| Dense embedding vector | Semantic sidecar | Store as rebuildable derived data |
| Generated answer | Perspective Memory or presentation/session layer | May be indexed only as a cited secondary interpretation; never treat as primary fact |
| Operational evidence | Hash-chained event ledger | Store identifiers and metrics, never document bodies |

## Retrieval modes

### Exact

Exact mode sends the user's query and filters to Recoll/Xapian and preserves its
ranking. It must work when Ollama and the semantic sidecar are unavailable.

### Prismatic

Prismatic mode is the default AI-assisted workflow:

1. Recoll/Xapian produces a bounded lexical candidate set.
2. The coordinator resolves candidate identities through `rcludi`.
3. Available candidate segments receive semantic scores from stored embeddings.
4. The coordinator combines lexical and semantic evidence with an explicit,
   configurable scoring policy.
5. Ollama may summarize, compare, identify contradictions, construct a timeline, or
   answer from the bounded evidence.
6. The UI retains the original Recoll rank and displays every source used by AI.

AI enrichment must never silently remove access to the unmodified Recoll results.

### Conceptual

Conceptual mode performs dense-vector retrieval across the semantic sidecar. It is
allowed to find evidence without shared query terms, but every result must resolve
back to a live `rcludi` in the active Recoll index before it can be displayed or
cited. Orphaned vectors are ignored and scheduled for cleanup.

## Minimal sidecar contract

The target semantic record contains only:

```text
Recoll profile identity
rcludi
source revision fingerprint
segment identifier and ordinal
source start and end offsets
segmenter version
embedding model and dimensions
dense embedding vector
```

Persisted segment text, title, path, and other Recoll metadata are transitional
duplication. They should be removed after evidence hydration from Recoll has been
implemented and validated. A cache may be introduced later only when bounded,
invalidated by source revision, and clearly marked non-authoritative.

The sidecar must be disposable. Deleting or rebuilding it must not modify original
files or the Xapian database.

Validated generated perspectives may occupy a separate secondary-memory namespace in
the sidecar. Their provenance and feedback restrictions are defined by the
[Perspective Memory Protocol](PERSPECTIVE_MEMORY.md). This exception does not make
the sidecar authoritative for document facts.

## Index and synchronization protocol

1. Recoll indexes and extracts documents first.
2. The semantic synchronizer enumerates a scoped Recoll query; it does not walk the
   filesystem as a competing inventory.
3. `rcludi` and a source revision fingerprint determine additions, changes, and
   removals.
4. Only changed documents are segmented and sent to the configured local Ollama
   embedding model.
5. Replacement of one document's semantic records is atomic.
6. A failed enumeration or embedding run must not delete previously valid records.
7. Model, dimension, or segmenter changes create a separate namespace or an explicit
   rebuild; incompatible vectors must never be mixed.
8. The Xapian database is opened through Recoll's supported API and is not modified
   by the AI subsystem.

## Presentation contract

The desktop interface exposes the three modes by user-facing name and shows which
layer produced each ranking. Exact results appear immediately. Prismatic and
Conceptual work runs asynchronously and remains cancellable.

Every AI response must provide:

- resolvable document and segment identifiers;
- source labels and offsets;
- a visible evidence list;
- a clear insufficient-evidence state; and
- access to the unchanged Recoll result set.

The interface must not imply that generated prose came from Xapian or from an
original document.

## Failure and privacy rules

- Recoll search continues if Ollama is stopped, slow, or returns malformed output.
- A missing or corrupt sidecar disables semantic modes, not Exact mode.
- No document body or private prompt is written to the project ledger.
- Models and document content remain local unless the user explicitly changes the
  local-only policy.
- Database paths, model names, candidate limits, and score weights are configurable.
- The AI subsystem must not write custom records into Recoll's Xapian database.

## Acceptance criteria

An implementation conforms to this protocol when:

1. Exact search reads the active Recoll profile and requires neither SQLite nor
   Ollama.
2. Prismatic mode begins with bounded Xapian candidates and preserves their original
   ranks for inspection.
3. Conceptual results are rejected when their `rcludi` no longer resolves.
4. The sidecar can be deleted and rebuilt exclusively from the Recoll inventory and
   the configured embedding model.
5. Search and answer outputs carry verifiable source identities and citations.
6. Tests demonstrate graceful degradation for unavailable Ollama, unavailable
   sidecar, stale vectors, and incompatible embedding namespaces.

## Implementation sequence

1. Add a lexical-search adapter that returns bounded, evidence-bearing Xapian
   candidates from the selected Recoll profile.
2. Add a hybrid coordinator and an explicit score-fusion policy.
3. Expose Exact, Prismatic, and Conceptual modes through the shared JSON command
   boundary and both desktop interfaces.
4. Hydrate result text and metadata from Recoll by `rcludi`.
5. Migrate the semantic schema to remove duplicated text and metadata.
6. Replace full vector scans with a local acceleration structure only when corpus
   measurements justify it; retain the exact implementation as the reference oracle.
