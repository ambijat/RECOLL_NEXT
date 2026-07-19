# Recoll Next session contract

This repository is an independent, local-first product derived from Recoll.

Before making changes, read [`SESSION_START.md`](SESSION_START.md). It is the
authoritative session briefing and links to the architecture, goal-fidelity covenant,
roadmap, and event-ledger specifications.

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
