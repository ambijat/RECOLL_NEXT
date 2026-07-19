# Prismatic Search Charter

## Status

This document fixes the fiduciary and product boundaries of Recoll Next's AI search
experience. It is normative: implementations may improve the mechanisms, but they
must preserve the duties and separations defined here.

## Product promise

Recoll Next is an evidence-exploration system.

- Recoll establishes what material exists and provides deterministic lexical evidence.
- Semantic retrieval discovers conceptually related material.
- Ollama organizes supplied evidence into useful perspectives.
- The user retains access to the original documents, unmodified results, and reasons
  each result was shown.

AI does not become the authority over the user's corpus. It acts as a local lens over
traceable evidence.

## Fiduciary duties

The system acts on private knowledge entrusted to it. Every feature must honor these
duties.

### Fidelity

- Never present generated interpretation as indexed fact.
- Never invent a document, passage, author, date, path, or citation.
- Preserve the user's original query alongside any derived query.
- Clearly distinguish source metadata, retrieved excerpts, inferred relationships,
  and generated prose.

### Evidence

- Every generated factual claim must cite one or more supplied segment identifiers.
- Every citation must resolve to a document in the active Recoll index.
- Citation validation happens before generated content reaches the interface.
- When evidence is absent, conflicting, or insufficient, say so explicitly.

### Privacy

- Document content remains local by default.
- Ollama endpoints must be loopback-only unless the user deliberately changes policy.
- Cloud models and web search are disabled in the default product configuration.
- Full documents, private passages, and prompts are excluded from logs and the event
  ledger.

### User control

- Lexical search remains available when Ollama is stopped or unavailable.
- Users can see the unmodified Recoll result order.
- Users choose whether to request synthesis; it is not forced onto every query.
- Users can move between exact, balanced, conceptual, and exploratory retrieval.
- AI-derived clusters and labels can be dismissed without affecting the index.

### Provenance

- The interface explains why each result appeared.
- Retrieval mode, model identity, source segment, and transformation stage remain
  inspectable.
- Privacy-safe lifecycle and integrity events are recorded in the hash-chained ledger.
- Derived semantic data can be rebuilt; original files and the Recoll index remain
  authoritative.

## The Polaroid and Prism model

### Polaroid: the evidence card

Every result begins as a stable factual snapshot containing available source data:

- document title and path;
- date, author, MIME type, and indexed metadata;
- exact matching terms and relevant source passage;
- lexical and semantic retrieval scores;
- retrieval provenance and the reason the result appeared.

The Polaroid layer contains no AI-created facts. It must be usable independently of
all Prism features.

### Prism: selectable interpretations

Ollama may organize the retrieved evidence through explicit lenses:

- **Exact** — traditional Recoll relevance and literal matches.
- **Concept** — materially similar ideas expressed with different language.
- **Timeline** — evidence arranged as an evolving sequence.
- **People** — evidence grouped by people or organizations.
- **Decision** — decisions, approvals, alternatives, and rejections.
- **Action** — commitments, tasks, deadlines, and unresolved work.
- **Agreement** — independently retrieved material supporting a shared conclusion.
- **Contradiction** — conflicting statements or changes in position.
- **Origin** — primary material separated from repetition or commentary.
- **Novelty** — relevant evidence outside the dominant cluster.

A lens is an interpretation of evidence, not a mutation of it. Selecting a lens must
never hide access to the underlying Polaroid cards.

## Retrieval topology

Recoll and semantic retrieval operate in parallel. A strictly sequential pipeline is
not sufficient because Ollama cannot recover conceptually relevant documents that a
literal first pass never retrieved.

```text
                         +-- Recoll: terms, fields, names, metadata
User query -> query core |
                         +-- Semantic index: concepts and related language
                                      |
                              combined evidence
                                      |
                          Ollama perspective lenses
                                      |
                       cited prismatic presentation
```

The original query is immutable. Ollama may propose derived interpretations such as
synonyms, adjacent concepts, actors, or time frames. Derived queries are labeled and
executed as additional retrieval paths rather than silently replacing user intent.

## Progressive interaction

The desktop experience reveals layers as they become available:

1. Recoll lexical results appear immediately.
2. Semantic candidates merge into the result set.
3. Hybrid ranking and deduplication settle the evidence order.
4. Clusters and perspective lenses appear progressively.
5. A cited synthesis is generated only when the user requests it.

Model latency must not block ordinary desktop search. Cancellation must be available
for embedding, semantic retrieval, and generation operations.

## Retrieval modes

The interface exposes a comprehensible Exact-to-Conceptual control:

- **Exact** — unmodified lexical results dominate.
- **Balanced** — lexical and semantic rankings are fused.
- **Conceptual** — semantic similarity receives greater influence.
- **Exploratory** — relevant adjacent and novel clusters are deliberately included.

The initial fusion method should be reciprocal-rank fusion. Raw lexical scores and
vector distances must not be treated as directly comparable measurements.

## Cited synthesis contract

An answer operation receives a bounded set of evidence segments and returns a
machine-readable structure equivalent to:

```json
{
  "answer": "A synthesis grounded in retrieved evidence.",
  "citations": [
    {
      "segment_id": "document-id:segment-4",
      "claim": "The statement supported by this segment"
    }
  ],
  "insufficient_evidence": false
}
```

Before display, the application validates that every cited segment was supplied to
the model and still resolves through the active index. Invalid citations make the
response invalid; they are not silently removed to make an answer appear trustworthy.

## Example scenario

For the query `Why was the product deployment delayed?`:

- Recoll may find literal references to deployment, delay, and the product name.
- Semantic retrieval may also find `release moved to next quarter`, `security approval
  remains outstanding`, or `migration cannot proceed before validation`.
- The Timeline lens may arrange those passages chronologically.
- The Action lens may expose unresolved approvals and owners.
- The Contradiction lens may show that one source attributes the delay to a vendor
  while another attributes it to internal validation.

Every statement remains connected to its Polaroid evidence card and original file.

## Failure behavior

- If Ollama is unavailable, show lexical results and a local-runtime diagnostic.
- If semantic storage is corrupt or incompatible, retain lexical search and offer a
  rebuild of derived data.
- If generation times out, keep retrieved evidence visible.
- If citations fail validation, suppress the synthesis and show the validation error.
- If sources conflict, surface the conflict rather than selecting a preferred story.

## Non-goals

Recoll Next is not:

- a chatbot that answers without retrieval;
- an autonomous authority over private documents;
- a replacement for original files or the lexical index;
- a system that silently sends content to remote services;
- a mechanism for hiding uncertainty behind fluent prose;
- a distributed cryptocurrency or consensus network.

## Acceptance criteria

The prismatic search milestone is complete only when:

1. Exact search works with Ollama completely stopped.
2. Semantic retrieval finds reference-corpus concepts absent from literal results.
3. Every hybrid result exposes lexical/semantic provenance.
4. Users can recover the unmodified Recoll ordering.
5. Each perspective statement links to source segments.
6. Fabricated or unresolved citations are rejected before display.
7. Conflicting evidence is visible and is not collapsed into false certainty.
8. No private content appears in diagnostic logs or ledger payloads.
9. Default configuration rejects non-loopback Ollama endpoints and cloud models.
10. Model and semantic-index failures never destroy or disable the lexical index.

## Change control

Changes that weaken a fiduciary duty, citation rule, privacy boundary, or lexical
fallback require an explicit architecture decision recorded in documentation and the
event ledger. Performance or interface convenience alone is not sufficient reason to
weaken these guarantees.
