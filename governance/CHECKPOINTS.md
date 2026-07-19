# Governance ledger checkpoints

Each entry records a ledger head verified from genesis. A checkpoint is historical:
later appends do not modify earlier entries.

| UTC date | Events | Head SHA-256 | Meaning |
|---|---:|---|---|
| 2026-07-19 | 6 | `9bebafe37b1781a80a8b6a591745e2505ae23262b38f8b58cf2e94240cc192b5` | Initial mission, charter decision, implementation milestones, and fidelity covenant. |
| 2026-07-19 | 7 | `0c065f78ebd3d455c133d8df848dd9ac812e2580ab0823ec8acb9bfda88afbcc` | Governance foundation committed locally as `80c5a5e40304ab8ed3db217efcd79bcfac24a114`. |

Verify the current head before adding another row:

```text
python src/semantic/rclsem_ledger.py verify governance/events.jsonl
```
