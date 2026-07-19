# Recoll Next architecture

## Product boundary

Recoll Next is a local knowledge-retrieval application, not a fork that continually
tracks upstream. The inherited Recoll engine remains the stable foundation. New
capabilities should be attached through explicit adapters so the core index remains
usable even when Ollama or the vector store is unavailable.

The evidence, privacy, and user-control boundaries are defined normatively by the
[Prismatic Search Charter](PRISMATIC_SEARCH.md).
The retrieval ownership and hybrid-ranking boundary are defined normatively by the
[Xapian-first Hybrid Search Protocol](XAPIAN_FIRST_PROTOCOL.md).
Cross-machine reconstruction and artifact ownership are governed by the
[Portability Contract](PORTABILITY_CONTRACT.md).

## Logical layers

1. **Acquisition and extraction** — inherited Recoll filters normalize files and
   metadata.
2. **Lexical index** — Xapian/Recoll remains the authoritative document inventory and
   keyword search engine.
3. **Semantic index** — document segments and embeddings provide similarity search.
   The vector store is derived data and must always be rebuildable.
4. **Retrieval coordinator** — combines lexical and semantic candidates, applies
   filters, deduplicates documents, and produces evidence-bearing ranked results.
5. **Local model runtime** — an Ollama adapter handles embedding, reranking, and
   generation. No model name or endpoint is hard-coded at product boundaries.
6. **Answer composer** — builds bounded context from retrieved segments and returns
   an answer plus document/segment citations. It must be able to decline when evidence
   is insufficient. The initial implementation rejects malformed output, invented
   segment identifiers, and supported answers without citations.
7. **Perspective memory** — stores validated, cited AI interpretations and their
   embeddings as secondary local memory. Stale source revisions suppress retrieval;
   prior interpretations never replace primary evidence.
8. **Presentation and API** — the Qt AI Perspective dock and runnable desktop
   companion consume the same JSON retrieval and answer contracts. Model work runs in
   a child process so ordinary Recoll search stays responsive and independent.
9. **Event ledger** — cross-cutting, append-only evidence about operations and
   decisions. It does not store indexed content and is not used as application state.

## Source-of-truth rules

- Original files are the content source of truth.
- Recoll is the document identity and searchable metadata source of truth.
- The semantic sidecar is not a second document authority. Its current schema includes
  transitional extracted-text/title/path caches plus rebuildable vector coordinates,
  model metadata, and explicitly secondary Perspective Memory.
- Embeddings and generated answers are derived artifacts.
- The event ledger is the audit source of truth for actions that occurred.

## Failure isolation

- Recoll lexical search must continue when Ollama is stopped.
- A corrupt or incompatible semantic index must be rebuildable without touching the
  Recoll index.
- Ledger-write failure must be visible. For security-relevant administrative actions,
  fail closed; for read-only search telemetry, return the result and emit a prominent
  diagnostic.
- Model timeouts and malformed responses must become typed errors, not empty results.

## Stable identifiers

Use Recoll's `rcludi` as the document identity while it is valid. A segment identity
must also include a segmentation-version identifier and source revision fingerprint.
Embedding collections must be namespaced by configuration, embedding model, vector
dimension, and segmentation version.

## Privacy

All content processing is local by default. Configuration must distinguish an Ollama
endpoint on loopback from a remote endpoint and require an explicit policy change for
the latter. Logs and ledger events contain identifiers and measurements, not full
content.

The implemented segmentation, namespace, and synchronization invariants are specified
in the [Semantic Index Foundation](SEMANTIC_INDEX.md). The inventory and evidence
query contracts are specified in [Semantic Retrieval](SEMANTIC_RETRIEVAL.md).
The generation and validation boundary is specified in
[Local Cited Answers](CITED_ANSWERS.md).
The secondary interpretation boundary is specified in
[Perspective Memory](PERSPECTIVE_MEMORY.md).
The complete implementation ownership map is specified in the
[Component Catalog](COMPONENT_CATALOG.md).
The presentation child-process envelopes are specified in the
[Local CLI and JSON API Contract](API_CONTRACT.md).
