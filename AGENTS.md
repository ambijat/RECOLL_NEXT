# Recoll Next session contract

This repository is an independent, local-first product derived from Recoll.

## Mandatory agent bootstrap

Before any repository mutation, every human or AI agent must completely read:

1. [`SESSION_START.md`](SESSION_START.md);
2. [`docs/PORTABILITY_CONTRACT.md`](docs/PORTABILITY_CONTRACT.md);
3. [`docs/AGENT_HANDOFF.md`](docs/AGENT_HANDOFF.md); and
4. every document listed under **Required reading** in `SESSION_START.md`.

Read-only orientation may precede completion of this list. No file edit, generated
artifact, dependency installation, runtime-store mutation, commit, or external action
may occur before it is complete. Conversation history or an agent summary does not
replace the tracked reading set.

`SESSION_START.md` is the authoritative session briefing. The documentation map in
[`docs/README.md`](docs/README.md) defines each contract and operational reference.

## Non-negotiable rules

- Do not fetch, pull, push, open pull requests, or otherwise contact a Git remote.
- Preserve upstream history as lineage only. New product decisions are made here.
- Preserve unrelated working-tree changes; inspect before editing overlapping files.
- Keep indexed document content and prompts local by default.
- Record product events through the hash-chained event ledger as subsystems are
  instrumented. Never put secrets or full document bodies in ledger payloads.
- Prefer small, testable boundaries around the existing Recoll engine.
- Ollama is the default model runtime; model names and endpoints must remain
  configurable.
- Test proposed work against `docs/GOAL_FIDELITY.md`; do not weaken an invariant
  without the documented change-control process.

## Session completion

Update `SESSION_START.md` when architecture, operating rules, major risks, or the
current milestone changes. Record major goals, decisions, and milestones in the
project governance ledger and verify its head before milestone commits.
