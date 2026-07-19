# Goal Fidelity Covenant

## Purpose

This covenant prevents implementation momentum from silently changing the product's
original purpose. It translates the mission and Prismatic Search Charter into durable
engineering invariants, evidence requirements, and regression gates.

The project succeeds only when its capabilities increase without weakening these
commitments.

## Authority order

When documents appear to conflict, interpret them in this order:

1. The mission and non-negotiable rules in `SESSION_START.md` and `AGENTS.md`.
2. Fiduciary duties in `docs/PRISMATIC_SEARCH.md`.
3. System boundaries in `docs/ARCHITECTURE.md`.
4. The invariants and gates in this covenant.
5. Milestone sequencing in `docs/ROADMAP.md`.
6. Implementation notes and source comments.

The hash-chained governance ledger proves which major goals, decisions, and milestones
were recorded. It does not override the governing documents.

## Fidelity matrix

| Original goal | Steadfast invariant | Present evidence | Regression gate |
|---|---|---|---|
| Private desktop knowledge | Indexed content, prompts, and answers remain local by default. | Loopback-only Ollama policy and local SQLite semantic store. | Reject non-loopback endpoints, cloud models, credentials in URLs, and private payloads in logs or ledger events. |
| Recoll as base camp | Recoll remains authoritative for document identity, extraction, metadata, and lexical retrieval. | Architecture source-of-truth rules and preserved Recoll engine. | No AI feature may mutate original files or make lexical search depend on Ollama. |
| Ollama as perspective layer | AI interprets evidence; it does not become the source of record. | Polaroid/Prism separation in the charter. | Generated statements must remain visibly distinct from indexed metadata and source excerpts. |
| Prismatic viewing | Users can rotate among exact, conceptual, timeline, people, decision, action, agreement, contradiction, origin, and novelty lenses. | Normative lens definitions in the charter. | A lens cannot hide access to the underlying evidence cards or silently replace the original query. |
| Faithful answers | Every generated factual claim resolves to supplied evidence. | Cited synthesis contract. | Reject the entire synthesis when cited segment identifiers were not supplied or cannot resolve through the active index. |
| Search resilience | Ordinary desktop search works when Ollama is stopped, slow, or broken. | Failure-isolation architecture. | Lexical results appear independently and are never delayed behind model startup or generation. |
| User agency | AI enrichment is inspectable, cancellable, and optional. | Progressive interaction and Exact-to-Conceptual controls. | Users can recover unmodified Recoll ordering and cancel model operations without damaging either index. |
| Rebuildable intelligence | Embeddings, clusters, and answers are derived artifacts. | Versioned SQLite namespaces and deterministic segment identities. | Model, dimension, or segmenter incompatibility creates/requires a new namespace rather than corrupting existing data. |
| Complete synchronization | Semantic state reflects additions, changes, and deletions from the authoritative inventory. | Incremental synchronizer and regression tests. | Repeated passes embed nothing unchanged; changed documents replace atomically; stale deletion runs only after complete enumeration. |
| Tamper-evident history | Important decisions and product events form a verifiable local chain. | `governance/events.jsonl` and the event-ledger implementation. | Sequence, previous hash, event hash, and checkpoint head must verify before a milestone commit. |
| Independent development | Historical upstream data is lineage, not operational authority. | Session contract and local commits. | No fetch, pull, push, PR, or remote API operation without a new explicit user instruction that changes repository policy. |

## Decision test

Before introducing a feature or dependency, answer:

1. Which original goal does it advance?
2. Which invariant constrains it?
3. What source remains authoritative?
4. What happens when Ollama or the new component is unavailable?
5. How can the user inspect, cancel, or bypass it?
6. What private data crosses the component boundary?
7. What event is recorded without storing private content?
8. What automated test proves the relevant regression gate?

If these questions do not have concrete answers, the feature is not ready to enter the
implementation roadmap.

## Drift indicators

Stop and review the architecture when any of these appear:

- generated prose is displayed without resolvable evidence;
- a model response overwrites indexed metadata;
- semantic search becomes a prerequisite for exact search;
- a convenience feature sends content outside loopback by default;
- raw prompts, passages, paths, or credentials enter telemetry or the ledger;
- changing models silently reuses incompatible vectors;
- an AI-generated interpretation cannot be dismissed or traced;
- a major architectural change is committed without a decision event;
- documentation describes aspirations that tests no longer enforce.

## Milestone fidelity review

Before each milestone commit:

1. Run all focused tests with resource warnings treated as errors.
2. Verify `governance/events.jsonl` from genesis to head.
3. Compare changed behavior with every row in the fidelity matrix.
4. Add architecture or policy decisions to the ledger.
5. Record the milestone event with its commit identifier when available.
6. Add the verified ledger head to `governance/CHECKPOINTS.md`.
7. Update `SESSION_START.md` if state, risks, or the active milestone changed.

The automated governance tests verify the chain, preserve the original goal as the
genesis event, and require the current head to appear in the human-readable checkpoint
table.

## Change control

Strengthening an invariant requires documentation, tests, and a governance event.
Weakening an invariant requires explicit user direction, a written architecture
decision explaining the tradeoff, updated acceptance criteria, and a hash-chained
decision event. Silence or implementation convenience never constitutes approval.
