# Recoll Next documentation map

This directory documents the rebuilt Recoll Next product. Inherited product manuals
were intentionally removed; the source code and legally required provenance remain.

## Mandatory orientation

Every human or AI agent must read these documents before changing the repository:

1. [`../AGENTS.md`](../AGENTS.md) — non-negotiable repository contract.
2. [`../SESSION_START.md`](../SESSION_START.md) — current state, milestone, and risks.
3. [`PORTABILITY_CONTRACT.md`](PORTABILITY_CONTRACT.md) — preservation and transfer
   invariants.
4. [`AGENT_HANDOFF.md`](AGENT_HANDOFF.md) — session entry, evidence, and handoff
   protocol.

After orientation, read the documents routed by the task.

## Normative product contracts

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — logical layers and sources of truth.
- [`GOAL_FIDELITY.md`](GOAL_FIDELITY.md) — fiduciary product covenant and change
  control.
- [`PRISMATIC_SEARCH.md`](PRISMATIC_SEARCH.md) — evidence and presentation charter.
- [`XAPIAN_FIRST_PROTOCOL.md`](XAPIAN_FIRST_PROTOCOL.md) — authoritative lexical and
  hybrid retrieval boundary.
- [`PERSPECTIVE_MEMORY.md`](PERSPECTIVE_MEMORY.md) — generated secondary-memory
  boundary.
- [`EVENT_LEDGER.md`](EVENT_LEDGER.md) — tamper-evident event format and privacy
  rules.

## Portability and operations

- [`PORTABILITY_CONTRACT.md`](PORTABILITY_CONTRACT.md) — master migration contract.
- [`WORKSTATION_BASELINE.md`](WORKSTATION_BASELINE.md) — verified source-machine
  snapshot and current limitations.
- [`DEVELOPMENT_AND_BUILD.md`](DEVELOPMENT_AND_BUILD.md) — environment creation,
  builds, and tests.
- [`CONFIGURATION_REFERENCE.md`](CONFIGURATION_REFERENCE.md) — paths, environment,
  CLI, schemas, and defaults.
- [`API_CONTRACT.md`](API_CONTRACT.md) — stable CLI JSON envelopes and process rules.
- [`DATA_MIGRATION.md`](DATA_MIGRATION.md) — cold-copy, rebuild, verification, and
  rollback procedures.
- [`TRANSFER_MANIFEST_TEMPLATE.md`](TRANSFER_MANIFEST_TEMPLATE.md) — reusable private
  migration evidence template.
- [`OPERATIONS_RUNBOOK.md`](OPERATIONS_RUNBOOK.md) — routine startup, indexing,
  synchronization, search, backup, and recovery.
- [`AGENT_HANDOFF.md`](AGENT_HANDOFF.md) — mandatory cross-agent continuity protocol.
- [`COMPONENT_CATALOG.md`](COMPONENT_CATALOG.md) — implemented, inherited, legacy,
  planned, and test component ownership.
- [`SECURITY_AND_PRIVACY.md`](SECURITY_AND_PRIVACY.md) — assets, trust boundaries,
  threats, controls, and residual risks.
- [`PROVENANCE_AND_LICENSING.md`](PROVENANCE_AND_LICENSING.md) — lineage and legal
  artifact preservation.

## Implemented feature references

- [`LOCAL_AI_RUNTIME.md`](LOCAL_AI_RUNTIME.md) — local Ollama policy and adapter.
- [`SEMANTIC_INDEX.md`](SEMANTIC_INDEX.md) — segmentation and incremental vector
  synchronization.
- [`SEMANTIC_RETRIEVAL.md`](SEMANTIC_RETRIEVAL.md) — Recoll bridge and cosine search.
- [`CITED_ANSWERS.md`](CITED_ANSWERS.md) — bounded generation and citation validation.
- [`AI_WORKSPACE.md`](AI_WORKSPACE.md) — native and runnable desktop presentations.

## Planning and governance

- [`ROADMAP.md`](ROADMAP.md) — staged implementation plan.
- [`../governance/README.md`](../governance/README.md) — project ledger rules.
- [`../governance/CHECKPOINTS.md`](../governance/CHECKPOINTS.md) — independently
  readable chain heads.

## Documentation status convention

“Implemented” means code and automated tests exist. “Live validated” means the
operation was also exercised against the workstation's real Recoll/Ollama runtime.
“Planned” means the document constrains future work but no complete implementation is
claimed. Documentation must preserve these distinctions.
