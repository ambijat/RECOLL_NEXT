# Recoll Next portability contract

## Authority

This is the master contract for moving Recoll Next between desktop machines, storage
layouts, Python runtimes, local model installations, or AI development agents. It is
mandatory reading under `AGENTS.md`.

Portability means preserving declared behavior and provenance, not merely copying a
directory. A transfer is complete only after the destination passes the acceptance
checks for the fidelity levels claimed by the operator.

## Non-negotiable invariants

1. Original files remain the content source of truth.
2. The selected Recoll profile and Xapian database remain the document identity,
   extraction, metadata, and lexical retrieval authority.
3. Semantic vectors, perspective memories, and generated answers remain derived
   local artifacts.
4. Ollama endpoints and model names remain configurable and local-only by default.
5. The project and runtime ledgers retain their distinction and must verify before
   and after transfer.
6. No migration procedure may contact a Git remote. Source history moves through a
   verified local copy or local Git bundle.
7. A virtual environment, compiled binary, Xapian database, or Ollama model directory
   is never assumed portable across incompatible operating systems or runtime ABIs.
8. Unknown compatibility is reported and rebuilt; it is never silently accepted.
9. Private corpus content, prompts, and generated perspectives are transferred only
   when the operator deliberately includes their data capsule.
10. Every destination receives the mandatory agent contract and documentation with
    the source history.

## Portable units

Recoll Next consists of independent capsules. An operator must declare which capsules
are being moved.

| Capsule | Contents | Authority | Default transfer policy |
| --- | --- | --- | --- |
| Source | Working tree plus `.git` history | Product source and decisions | Always preserve |
| Governance | `governance/events.jsonl` and checkpoints | Project event evidence | Always preserve and verify |
| Corpus | User-selected original documents | Documentary truth | Copy independently with hashes when required |
| Recoll profile | `recoll.conf` and profile support files | Index scope and path configuration | Copy as a template, then rewrite paths |
| Xapian index | Recoll `dbdir` | Lexical index and `rcludi` identities | Prefer rebuild; cold-copy only under compatibility rules |
| Semantic sidecar | SQLite database under `.local` or chosen location | Rebuildable vectors and perspective memory | Prefer rebuild unless identity continuity is required |
| Runtime ledgers | `<store>.events.jsonl` | Local operational evidence | Copy with its sidecar when audit continuity is claimed |
| Ollama runtime | Executable, model manifests, and blobs | Local model execution | Reinstall and pull exact models; air-gap copying is separately validated |
| Python environment | Interpreter and installed packages | Development/runtime tooling | Recreate; do not copy `.venv` between machines |
| Native build | C++/Qt toolchain and produced binaries | Compiled presentation/runtime | Rebuild for destination ABI |

## Fidelity levels

A migration report must name the highest levels it actually verified.

### Level S — source fidelity

- All committed history is present.
- `git status --short` is clean or every intentional local file is separately listed.
- `AGENTS.md`, `SESSION_START.md`, this contract, and the governance chain exist.
- The source commit and ledger head equal the transfer manifest.

### Level L — lexical fidelity

- The destination Recoll profile resolves every intended `topdirs` entry.
- `dbdir` points to a valid destination Xapian database.
- Recoll and Xapian compatibility is known.
- Representative exact queries return expected documents.
- If the index was rebuilt, identical internal `rcludi` values are not assumed.

### Level A — AI retrieval fidelity

- Ollama is reachable under the local-only policy.
- Exact embedding and chat model identities are installed.
- Embedding dimensions match the semantic namespace.
- A semantic query returns evidence with resolvable primary sources.
- A cited answer rejects invented citations and exposes insufficient evidence.
- Perspective memories are treated as secondary and stale revisions are suppressed.

Model-family equality does not guarantee byte-identical generation. Record the
runtime version, full model tag, quantization, prompt contract, and relevant settings
when reproducibility matters.

### Level E — event fidelity

- The project governance chain verifies before and after transfer.
- Every transferred runtime ledger verifies independently.
- The transfer manifest records chain counts and head hashes.
- Lock files are not evidence and need not be transferred.

### Level B — binary/UI fidelity

- The destination toolchain can build the native Qt application, or an explicitly
  recorded compatible binary is used.
- The AI Perspective dock is present in the build.
- The Tk companion launches with the destination Python/Tk runtime.
- Search, cancellation, evidence opening, and Markdown export are exercised.

## Supported migration strategies

### Clean rebuild — recommended

Move source, governance, configuration intent, corpus, and model inventory. Reinstall
Recoll and Ollama, rewrite paths, rebuild Xapian, recreate the Python environment,
and regenerate semantic vectors. This minimizes ABI and stale-identity risk.

Tradeoff: rebuilding Xapian and embeddings can be time-consuming, and regenerated
`rcludi` identities may invalidate copied perspective memories.

### Warm transfer

Move the source plus a cold copy of the Recoll profile, compatible Xapian database,
semantic sidecar, runtime ledgers, and corpus under equivalent path mappings. Use
only when the destination Recoll/Xapian versions and filesystem semantics are
compatible and preserving identities materially matters.

Tradeoff: fastest continuity, highest risk of hidden path, ABI, or stale-revision
coupling. The full Level L/A acceptance suite is mandatory.

### Air-gapped transfer

Move every required installer, source bundle, corpus capsule, configuration template,
and model artifact on controlled media. Verify hashes on both sides. The currently
validated project path assumes models can be installed before the machine becomes
offline. Direct copying of Ollama's internal model store is not yet certified by this
project and must be logged as an explicit migration experiment.

## Compatibility matrix

| Artifact | Same machine paths | Same OS required | Same ABI/runtime required | Safe default |
| --- | --- | --- | --- | --- |
| Markdown/source files | No | No | No | Copy with Git history |
| `.git` object database | No | No | Git-compatible | Local copy or bundle |
| `.venv` | Often | Usually | Yes | Recreate |
| Recoll profile | No; rewrite | No | No | Copy as template |
| Xapian Glass database | Path mapping matters | Strongly preferred | Compatible Xapian/Recoll | Rebuild |
| Semantic SQLite sidecar | No | No | Compatible SQLite schema and embeddings | Rebuild or verified cold-copy |
| Runtime JSONL ledger | No | No | UTF-8 and verifier | Copy and verify |
| Ollama model store | Configurable | Runtime-dependent | Ollama-format compatibility | Re-pull exact models |
| Native Recoll executable | Yes | Yes | Compiler/Qt/Xapian ABI | Rebuild/reinstall |
| Tk companion | No | Python/Tk available | Supported Python | Recreate environment |

## Transfer manifest

Every material move must create a Markdown manifest outside or beside the transfer
capsule. At minimum record:

```text
Transfer date and operator
Source and destination machine identifiers chosen by the operator
Migration strategy and claimed fidelity levels
Git commit and branch
Working-tree status and intentionally untracked files
Project ledger event count and head hash
Recoll and Xapian versions
Recoll configuration directory, dbdir, and topdirs mapping
Corpus roots, file counts, byte totals, and optional hash-manifest path
Semantic store paths, sizes, schema, model, dimensions, and runtime ledger heads
Ollama version and exact installed model tags/quantizations
Python, SQLite, and Tk versions
Native build toolchain versions or an explicit “not available” statement
Acceptance checks, results, deviations, and rollback location
```

Do not put secrets or unrestricted private document listings in the project ledger.
Keep corpus-level manifests with the private transfer media when filenames themselves
are sensitive.

## Source transfer rules

Before source transfer:

```powershell
git status --short
git log -1 --format="%H %s"
python src\semantic\rclsem_ledger.py verify governance\events.jsonl
```

A direct cold copy must include `.git`, tracked files, and intentional untracked
files, while excluding disposable `.venv`, build outputs, and `.local` unless those
capsules were selected.

A branch-scoped local Git bundle preserves the complete history reachable from the
selected product branch without contacting a remote or exporting unrelated local,
remote-tracking, or agent-checkpoint refs:

```powershell
git bundle create recoll-next.bundle master
git bundle verify recoll-next.bundle
```

Replace `master` only with the explicitly selected local product branch. Do not use
`--all` by default: development environments may contain remote-tracking or tool-owned
refs that are not part of the intended transfer capsule. Record the exported ref and
tip commit in the manifest.

Uncommitted and ignored files are not included in a Git bundle. Commit intentional
source changes or list and copy them separately. On the destination, cloning from the
bundle is a local operation; no network remote is authorized by this protocol.

## Data consistency rules

- Stop Recoll indexing, GUI AI jobs, semantic synchronization, and any process using
  a selected SQLite store before a raw file copy.
- Never copy only one file from an active SQLite WAL set. This implementation does
  not request WAL mode, but migration must inspect for `-wal` and `-shm` siblings.
- Never edit Xapian Glass files individually.
- Copy the whole Recoll `dbdir` only while writers are stopped.
- Preserve the runtime ledger beside its semantic store when operational continuity
  is claimed.
- Rebuild semantic data when `rcludi`, source revision, segmenter, embedding model,
  or vector dimensions are not demonstrably compatible.

## Destination acceptance gate

A migration is not accepted until all selected checks pass:

```powershell
git status --short
python src\semantic\rclsem_ledger.py verify governance\events.jsonl
python -W error::ResourceWarning -m unittest discover -s tests\semantic
python src\semantic\recoll_ai.py doctor
```

Then validate the selected Recoll profile, run a bounded semantic synchronization or
search, obtain one cited answer, verify every transferred runtime ledger, and launch
the intended GUI. Detailed commands and failure handling live in
[`DATA_MIGRATION.md`](DATA_MIGRATION.md) and
[`OPERATIONS_RUNBOOK.md`](OPERATIONS_RUNBOOK.md).

## Rollback and evidence

Never overwrite the only working capsule during migration. Preserve the source
machine and immutable transfer media until destination acceptance. If verification
fails:

1. Stop destination writers.
2. Preserve the failed files and logs without putting private bodies in Git.
3. Identify the first failed fidelity level.
4. Prefer rebuilding the derived layer rather than repairing Xapian, SQLite vectors,
   or a hash chain in place.
5. Record material architectural deviations in the project ledger and operational
   failures in the affected runtime ledger when safe.

## Change control

Any change to sources of truth, default privacy, transfer compatibility, mandatory
reading, or acceptance gates requires:

1. an update to this contract and affected runbooks;
2. tests or a documented reason a check cannot run;
3. an `architecture.decision.*` project-ledger event; and
4. a local checkpoint commit. No remote action is part of this process.
