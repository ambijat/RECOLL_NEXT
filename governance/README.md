# Project governance ledger

`events.jsonl` is the versioned, append-only SHA-256 chain for durable project goals,
architectural decisions, and completed milestones. Runtime search/index/model events
belong in each local product profile's separate ledger and must not be committed.

Verify the project chain from the repository root:

```text
python src/semantic/rclsem_ledger.py verify governance/events.jsonl
```

Append through `EventLedger` or the ledger CLI only. Never edit, reorder, reformat, or
truncate existing lines. The sibling `.lock` file is runtime coordination state and is
ignored by Git.

The chain demonstrates internal integrity. Git commits and the independently readable
head hashes in `CHECKPOINTS.md` make wholesale replacement more detectable. Future
milestones may add asymmetric signatures held outside the repository.

## Allowed project events

- `project.goal.*` — original or explicitly revised goals.
- `architecture.decision.*` — decisions that alter system boundaries.
- `milestone.*` — verified implementation milestones.
- `governance.notes.*` — creation or revision of normative governance notes.
- `ledger.checkpoint.*` — verification/checkpoint lifecycle.

Payloads may contain document names, decision identifiers, commit hashes, test counts,
and summarized non-sensitive outcomes. They must not contain source document content,
prompts, credentials, private paths, environment dumps, or unrestricted error text.
