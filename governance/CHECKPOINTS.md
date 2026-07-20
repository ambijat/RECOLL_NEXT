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
| 2026-07-19 | 12 | `e0478a4bf966ac6bf83f848da580e090ad8bf59cc90a3406caeef3a37e3183a4` | Windows bridge milestone `53d68526`; event 12 corrects the full commit reference recorded by event 11. |
| 2026-07-19 | 13 | `dd2c62431ef8c9188a5ab82ca2d0c4f4cf7725bdabffbc1f043fc6a981b277f8` | Validated local cited answers recorded as the customer-output evidence boundary. |
| 2026-07-19 | 14 | `5af399968a7bfb4ba19b09a502b53e36547315082cd76986f27717616237ce75` | Local cited-answer deliverable committed as `ca566f79` after 48 tests and live Ollama validation. |
| 2026-07-19 | 15 | `5b4aaa3f52c6a81ecfa85327775eafa3b1c4a84e740331488d71f37fd3ecc4d3` | Asynchronous AI Perspective UI recorded as the customer presentation boundary. |
| 2026-07-19 | 16 | `b19ef108e95217b594dfa985bc8faa560951c0665aba6bdd4b1348704ac6a87d` | Visible AI Perspective workspace committed as `92909a45`; runnable Tk GUI validated, native Qt source awaiting SDK compilation. |
| 2026-07-19 | 17 | `d2cdc02f894b3b991bfb3d35e0c4f4a1bbd0ab1fc1265917c6a5278e93492d8e` | Xapian-first hybrid retrieval recorded: Recoll remains authoritative and the Ollama vector sidecar remains minimal and rebuildable. |
| 2026-07-19 | 18 | `f420ebf62f447924fd593d1702500d977122dfedeff05d3d44de3a0b34a43c05` | Provenance-gated Perspective Memory recorded as secondary interpretation, never primary documentary evidence. |
| 2026-07-19 | 19 | `2dad13dc244efdbd2daf62a28763a64327ad2d2a5555aec7df4c34eb4b11b4e8` | Perspective Memory milestone committed as `95c83da0` after 59 tests and a live local embedding smoke test. |
| 2026-07-19 | 20 | `f813720751f9c0c8c964803d936b4d7ff41edef3989dedf03d60bf1b2f9c8597` | Portable source/data/model/build fidelity gates and mandatory tracked agent orientation recorded as the continuity contract. |
| 2026-07-19 | 21 | `4a4386257d1c7ca484ea8aeec608926fba463ef1cbf148df70e6bd35d81adf08` | Portable project and agent continuity suite committed as `b93379a6` with 25 Markdown documents and 63 passing tests. |
| 2026-07-20 | 22 | `94fddd8bb70839331aee1fbdf612e6bffda8c970c53fc1feb4474c26d0cbbfc7` | Audit debt-clearance milestone: retired Chroma implementation, offline-safe cross-platform bootstrap, and privacy-safe Perspective Memory read events with 68 passing tests. |

Verify the current head before adding another row:

```text
python src/semantic/rclsem_ledger.py verify governance/events.jsonl
```
