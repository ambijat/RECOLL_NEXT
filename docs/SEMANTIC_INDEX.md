# Semantic index foundation

## Scope

The semantic index is rebuildable local data derived from the authoritative Recoll
document inventory. This foundation provides deterministic segmentation,
model-versioned SQLite storage, incremental embedding synchronization, and
privacy-safe lifecycle events.

The live inventory adapter and similarity query layer are specified separately in
[Semantic Retrieval](SEMANTIC_RETRIEVAL.md).

The earlier Chroma implementation is retired. Its three former entry points are
bounded tombstones that direct callers to `recoll_ai.py sync` and `search`; they no
longer import Chroma or define a second semantic-store contract.

## Components

- `rclsem_segments.py` defines source documents, stable segments, and
  `token-window-v1` segmentation.
- `rclsem_store.py` owns the SQLite schema, namespaces, document revisions, segment
  text, offsets, and float32 embedding vectors.
- `rclsem_sync.py` compares the authoritative inventory with stored revisions and
  embeds only work that changed.
- `rclsem_events.py` connects semantic lifecycle events to the hash-chained ledger
  without exposing document content.
- `rclsem_ollama.py` supplies validated local batch embeddings.

## Deterministic segmentation

The first segmenter uses bounded token windows with preferred sentence endings and a
configurable overlap. Each segment retains:

- Recoll-compatible document identifier;
- document source revision;
- segmenter version;
- ordinal;
- source start and end character offsets;
- normalized segment text;
- SHA-256 segment identifier derived from those values.

Whitespace normalization affects only embedding text. Source offsets continue to
address the original extracted text. Changing content, title, path, or segmentation
version changes the derived identity and forces safe regeneration.

Default settings are 900 target characters and 150 overlap characters. These are
implementation defaults, not permanent product constants; changing segmentation
behavior requires a new segmenter version.

## Storage namespaces

Namespaces are derived from:

```text
embedding model + segmenter version
```

Vector dimensions are learned from the first non-empty embedding response and then
locked for that namespace. A different embedding model receives an independent
namespace. A dimension change inside an existing namespace is rejected before the
stored document is replaced.

The current SQLite tables are:

- `store_metadata` — schema version;
- `semantic_namespaces` — embedding model, segmenter version, and dimensions;
- `semantic_documents` — revision, title, path, segment count, and update time;
- `semantic_segments` — identity, offsets, local text, and packed float32 vector.

Foreign keys cascade segment deletion when a document is replaced or removed.

## Synchronization semantics

For each authoritative inventory pass:

1. Open or create the model/segmenter namespace.
2. Compare every source revision with its stored revision.
3. Skip unchanged documents without calling Ollama.
4. Segment new or changed documents deterministically.
5. Embed segments in bounded batches.
6. Replace each changed document atomically only after all its embeddings validate.
7. Delete stale documents only after the full source inventory completes.

If enumeration or embedding fails, stale deletion does not run. Previously committed
documents remain valid. An empty but successfully completed inventory is authoritative
and removes all documents when `delete_missing` is enabled.

## Audit events

When an event sink is configured, synchronization records:

- `index.semantic.started`;
- `index.semantic.completed`;
- `index.semantic.failed`.

Payloads contain namespace/model/version identifiers, counts, and error type only.
They exclude document text, segment text, prompts, paths, and exception messages.

## Verification evidence

Automated tests cover deterministic identities, source offsets, overlap, empty text,
batch limits, first synchronization, idempotent repetition, document replacement,
stale deletion, model isolation, dimension rejection, duplicate identifiers, Windows
SQLite handle closure, and privacy-safe events.

The complete semantic test suite currently has 40 passing tests. A live local check
against `embeddinggemma` produced 768-dimensional vectors for two synthetic documents;
the immediate second pass correctly produced zero new embeddings.
