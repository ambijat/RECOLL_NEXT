# Perspective Memory protocol

## Purpose

Perspective Memory turns validated local AI outputs into searchable, secondary
interpretations. It allows Recoll Next to recall previous summaries, decisions,
timelines, contradictions, and analyses without confusing generated prose with
primary documentary evidence.

The memory lives in the same local SQLite sidecar as semantic vectors. It never
changes Recoll's Xapian database.

## Epistemic boundary

A perspective is an interpretation, not a fact. It is admissible only when the
answer passed the cited-answer validator and contains at least one citation to a
retrieved primary segment.

Every stored perspective retains:

- its local question and generated answer;
- requested perspective view;
- chat and embedding model identities;
- creation time;
- cited `rcludi`, segment identifiers, and source revision fingerprints; and
- its dense embedding vector.

Perspective search dynamically checks those citations against the semantic document
inventory. If a cited segment or source revision no longer exists, that perspective
is suppressed. It is not silently treated as current knowledge.

Every memory query records a privacy-safe `search.memory.*` lifecycle. The event
contains a query digest, configured model and limit, result count and perspective
identifiers, or typed failure; it never contains the query, stored interpretation,
source text, path, embedding, or exception message.

## Retrieval policy

Perspective Memory is a secondary RAG layer:

```text
Primary evidence: source files -> Recoll/Xapian -> document segments
Secondary memory: validated cited answer -> perspective embedding -> SQLite
```

Future answer composition may retrieve both layers, but they must remain separately
labelled. A prior perspective may guide the requested angle or help locate primary
evidence; it cannot replace current primary evidence or satisfy the final citation
requirement. Generated perspectives must never recursively certify one another.

## Current behavior

A successful, sufficiently evidenced `ask` stores its perspective automatically.
Use `--no-remember` when the question or interpretation should remain ephemeral:

```text
python src/semantic/recoll_ai.py ask `
  --store .local/booklibrandom-pdfs.sqlite3 `
  --no-remember `
  "What competing interpretations appear in these papers?"
```

Search accumulated interpretations locally:

```text
python src/semantic/recoll_ai.py memory-search `
  --store .local/booklibrandom-pdfs.sqlite3 `
  "competing interpretations"
```

The shared JSON API returns `remembered` and `perspective_id` for a stored answer.
Exact duplicates are content-addressed and deduplicated.

The current milestone indexes and retrieves memories but deliberately does not feed
them into new answer prompts. That feedback step requires the hybrid coordinator to
label primary and secondary contexts independently and revalidate all primary
citations.

## Privacy and lifecycle

Questions and generated answers are stored locally because their text is necessary
for later retrieval and display. They are never copied into the project governance
ledger. Runtime events record only model/view identifiers, perspective identifiers,
and cited segment identifiers.

The sidecar remains derived local data. A future customer-facing memory manager must
support inspection, deletion, retention controls, and export before Perspective
Memory is enabled as an invisible background feature in a packaged release.

## Acceptance rules

- Insufficient or uncited answers are not remembered.
- A memory failure never suppresses an otherwise valid cited answer.
- Embedding models and dimensions are isolated by namespace.
- Stale or unverifiable citations suppress the perspective from retrieval.
- Perspective results are explicitly presented as prior AI interpretations.
- Primary evidence remains mandatory for factual claims in future RAG composition.
