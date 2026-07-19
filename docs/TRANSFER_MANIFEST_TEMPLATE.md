# Recoll Next transfer manifest

> Copy this template beside the private transfer capsule. Fill every applicable
> field. Do not commit private corpus listings, credentials, or unrestricted machine
> inventories to the project repository or governance ledger.

## Transfer identity

| Field | Value |
| --- | --- |
| Transfer identifier | `TODO` |
| Prepared UTC date/time | `TODO` |
| Operator | `TODO` |
| Source machine label | `TODO` |
| Destination machine label | `TODO` |
| Strategy | `clean rebuild / warm transfer / air-gapped` |
| Claimed fidelity levels | `S / L / A / E / B` |
| Planned downtime | `TODO` |
| Rollback location | `TODO` |

## Authorization and scope

- [ ] Source/history transfer authorized.
- [ ] Corpus transfer authorized.
- [ ] Recoll profile transfer authorized.
- [ ] Xapian cold-copy authorized, or clean rebuild selected.
- [ ] Semantic/Perspective Memory transfer authorized, or rebuild selected.
- [ ] Runtime-ledger transfer authorized.
- [ ] Ollama/model provisioning authorized.
- [ ] No Git remote operation is planned or authorized.
- [ ] Sensitive filenames/manifests will stay with private media.

## Source capsule

| Field | Value |
| --- | --- |
| Branch | `TODO` |
| Full Git commit | `TODO` |
| Commit subject | `TODO` |
| `git status --short` | `clean / attach intentional list` |
| Git bundle/copy path | `TODO` |
| Capsule SHA-256 | `TODO` |
| Bundle verification | `pass/fail/not used` |

## Governance evidence

| Field | Source value | Destination value |
| --- | --- | --- |
| Event count | `TODO` | `TODO` |
| Head hash | `TODO` | `TODO` |
| Ledger file SHA-256 | `TODO` | `TODO` |
| Verification result | `TODO` | `TODO` |

## Runtime versions

| Component | Source | Destination | Compatible/decision |
| --- | --- | --- | --- |
| Operating system | `TODO` | `TODO` | `TODO` |
| Git | `TODO` | `TODO` | `TODO` |
| Project Python | `TODO` | `TODO` | recreate `.venv` |
| Recoll-bundled Python | `TODO` | `TODO` | bridge validation |
| SQLite | `TODO` | `TODO` | schema validation |
| Tk | `TODO` | `TODO` | GUI validation |
| Recoll | `TODO` | `TODO` | `TODO` |
| Xapian | `TODO` | `TODO` | `rebuild/cold-copy` |
| Ollama | `TODO` | `TODO` | `TODO` |
| CMake/compiler/Qt | `TODO` | `TODO` | Level B or N/A |

## Model inventory

| Role | Exact tag | Parameters | Quantization | Destination validated |
| --- | --- | --- | --- | --- |
| Embedding | `TODO` | `TODO` | `TODO` | `yes/no` |
| Chat | `TODO` | `TODO` | `TODO` | `yes/no` |

| Field | Value |
| --- | --- |
| Endpoint | `TODO` |
| Local-only policy passed | `yes/no` |
| Embedding dimensions | `TODO` |
| Model acquisition method/authorization | `TODO` |

## Path mapping

| Purpose | Source | Destination | Validation |
| --- | --- | --- | --- |
| Repository | `TODO` | `TODO` | `TODO` |
| Recoll configuration | `TODO` | `TODO` | `TODO` |
| Xapian `dbdir` | `TODO` | `TODO` | `TODO` |
| Corpus root 1 | `TODO` | `TODO` | `TODO` |
| Additional corpus roots | `private attachment` | `private attachment` | `TODO` |
| Semantic store | `TODO` | `TODO` | `TODO` |
| Runtime ledger | `TODO` | `TODO` | `TODO` |

## Corpus capsule

| Field | Value |
| --- | --- |
| Private manifest path | `TODO` |
| Source file count | `TODO` |
| Destination file count | `TODO` |
| Source byte total | `TODO` |
| Destination byte total | `TODO` |
| Hash policy/result | `TODO` |
| Timestamp/ACL policy | `TODO` |

## Recoll/Xapian capsule

| Field | Value |
| --- | --- |
| Profile copied as template | `yes/no` |
| Every `topdirs` entry mapped | `yes/no` |
| Destination `dbdir` resolved | `TODO` |
| Strategy | `rebuild/cold-copy` |
| Writers stopped before copy | `yes/no/N/A` |
| Source database size/hash manifest | `TODO` |
| Configuration path check | `pass/fail` |
| Indexing result/errors | `TODO` |
| Representative exact queries | `pass/fail + private attachment` |

## Semantic and Perspective Memory capsule

| Field | Value |
| --- | --- |
| Strategy | `rebuild/cold-copy/archive only` |
| Store path and size | `TODO` |
| Store SHA-256 | `TODO` |
| SQLite schema version | `TODO` |
| Embedding model/dimensions | `TODO` |
| Segmenter/settings | `TODO` |
| Runtime ledger count/head | `TODO` |
| `rcludi` continuity proven | `yes/no/N/A` |
| Stale Perspective Memory check | `pass/fail/N/A` |

## Acceptance results

| Check | Command/evidence | Result |
| --- | --- | --- |
| Source commit | `git log -1` | `TODO` |
| Working tree | `git status --short` | `TODO` |
| Project chain | ledger `verify` | `TODO` |
| Full semantic tests | unittest discovery | `TODO` |
| Ollama readiness | `recoll_ai.py doctor` | `TODO` |
| Recoll exact search | representative cases | `TODO` |
| Semantic search | bounded sample | `TODO` |
| Cited answer | two-evidence sample | `TODO` |
| Perspective retrieval | `memory-search` | `TODO` |
| Runtime ledger(s) | ledger `verify` | `TODO` |
| Tk GUI | search/ask/cancel/open/export | `TODO` |
| Native GUI | rebuilt dock workflow | `TODO/N/A` |

## Deviations and known limitations

```text
TODO: Record every failed, skipped, or changed check and its impact on claimed
fidelity. Do not hide a rebuild discontinuity or incompatible copied artifact.
```

## Acceptance and rollback

- [ ] Only passing fidelity levels are claimed.
- [ ] Destination results were reviewed by the operator.
- [ ] Source/rollback capsules remain intact.
- [ ] Runtime data remains local and private.
- [ ] No Git remote was contacted.
- [ ] Deviations requiring an architecture decision were recorded safely.

| Decision | Value |
| --- | --- |
| Accepted/rejected | `TODO` |
| Accepted by | `TODO` |
| Acceptance UTC date/time | `TODO` |
| Rollback retained until | `TODO` |
| Next action | `TODO` |

