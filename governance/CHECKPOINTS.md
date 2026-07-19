# Governance ledger checkpoints

Each entry records a ledger head verified from genesis. A checkpoint is historical:
later appends do not modify earlier entries.

| UTC date | Events | Head SHA-256 | Meaning |
|---|---:|---|---|
| 2026-07-19 | 6 | `9bebafe37b1781a80a8b6a591745e2505ae23262b38f8b58cf2e94240cc192b5` | Initial mission, charter decision, implementation milestones, and fidelity covenant. |
| 2026-07-19 | 7 | `0c065f78ebd3d455c133d8df848dd9ac812e2580ab0823ec8acb9bfda88afbcc` | Governance foundation committed locally as `80c5a5e40304ab8ed3db217efcd79bcfac24a114`. |
| 2026-07-19 | 8 | `3e7fb0fb6d2792f3c07b524cc2a4fc225484056df7370e6c7c0a2aa63eee1a8b` | Exact cosine retrieval recorded as the reference-correct semantic ranking policy. |
| 2026-07-19 | 9 | `a946f13bf6069a07f45915029c8699715fc8a9644d17674e33c297db85dc4031` | Recoll inventory and semantic retrieval milestone committed locally as `74f34053`. |
| 2026-07-19 | 10 | `a78d2720375337a8b287de2a1a2fcdc2ba931e74eb0e2b531edd64eaa9cb47b8` | Windows Recoll bundled-Python bridge recorded as the ABI compatibility boundary. |

Verify the current head before adding another row:

```text
python src/semantic/rclsem_ledger.py verify governance/events.jsonl
```
