# Desktop-to-desktop data migration runbook

## Scope

This runbook moves Recoll Next without a Git remote. Read the master
[`PORTABILITY_CONTRACT.md`](PORTABILITY_CONTRACT.md) first and choose a clean rebuild,
warm transfer, or air-gapped transfer. Do not combine procedures casually: each
preserves different identities.

Examples use PowerShell. Substitute destination paths deliberately; never run a
recursive copy, delete, reset, or reindex command against an unresolved variable.

## Phase 1 — declare the migration

Create a private Markdown transfer manifest and record:

- selected capsules and migration strategy;
- claimed fidelity levels;
- source/destination storage mapping;
- whether corpus filenames are sensitive;
- whether Xapian `rcludi` continuity is required;
- whether prior Perspective Memory must survive;
- planned downtime and rollback location.

If identity continuity is not required, choose a clean rebuild.

## Phase 2 — audit the source

From the repository root:

```powershell
git status --short
git log -1 --format="%H %s"
python src\semantic\rclsem_ledger.py verify governance\events.jsonl
python -W error::ResourceWarning -m unittest discover -s tests\semantic
python src\semantic\recoll_ai.py doctor
```

Record exact runtime versions:

```powershell
python --version
git --version
ollama --version
ollama list
& 'C:\Program Files\Recoll\recollindex.exe' -h
```

Record the selected Recoll profile's `topdirs` and `dbdir`. Do not publish private
corpus paths in the project ledger.

For each selected file capsule, record byte size and SHA-256. For a small explicit
list:

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath governance\events.jsonl
Get-FileHash -Algorithm SHA256 -LiteralPath .local\semantic.sqlite3
```

For a private corpus tree, generate the detailed file manifest beside the private
transfer media rather than committing it to Git.

## Phase 3 — quiesce writers

Finish or cancel active operations through their normal interfaces:

- stop Recoll indexing/monitoring;
- close Recoll if the Xapian database will be copied;
- close the Tk companion and native AI jobs;
- stop semantic `sync`, `ask`, and `memory-search` processes;
- stop any backup or scanner touching the selected stores.

Confirm state with read-only process inspection. Do not terminate unrelated Python
or Ollama processes by name without identifying their exact command and owner.

Inspect the selected SQLite directory for `DATABASE-wal`, `DATABASE-shm`, or journal
siblings. A raw copy is allowed only after all writers are stopped. Copy the runtime
JSONL ledger beside the database; its `.lock` sibling is optional coordination state.

## Phase 4 — create the source capsule

### Committed source and history

Recommended local bundle:

```powershell
git bundle create recoll-next.bundle --all
git bundle verify recoll-next.bundle
Get-FileHash -Algorithm SHA256 -LiteralPath recoll-next.bundle
```

The bundle excludes ignored `.local`, `.venv`, `.idea`, and build products, and it
excludes uncommitted files. Handle every intentional exception explicitly.

A cold directory copy may be used instead, but it must include `.git` and must not
be performed while a commit is being created.

### Corpus

Copy original documents with an operator-selected backup tool that preserves required
timestamps and names. Avoid mirroring/deletion options on the first transfer. Compare
source and destination counts, byte totals, and—where fidelity requires—SHA-256
manifests.

### Recoll profile

Copy the configuration directory as a template. Preserve custom `fields`, `mimemap`,
`mimeconf`, `mimeview`, `backends`, and other intentionally modified profile files.
Do not assume cached status, PID, missing-file, or lock files are portable state.

### Xapian database: clean rebuild

Do not copy it. On the destination, install compatible Recoll, select a new empty
`dbdir`, map `topdirs`, validate paths, then run ordinary initial indexing. Do not
point the new profile at the only source database.

### Xapian database: warm transfer

Copy the complete `dbdir` as one cold capsule only when:

- writers are stopped;
- Recoll and Xapian versions are compatible;
- destination filesystem semantics are compatible;
- corpus path mapping is equivalent or Recoll path translation is configured;
- there is enough free space for both the capsule and rollback copy.

Never select individual `.glass` files. Hash or size-check the complete directory.

### Semantic sidecar and Perspective Memory

For a clean rebuild, do not transfer the SQLite sidecar. Recreate it from the new
Recoll inventory, which prevents stale `rcludi` and revision coupling.

For a warm transfer, copy the stopped SQLite database and its runtime ledger. Record
the embedding model, vector dimension, segmenter settings, and ledger head. The
destination must prove that cited `rcludi`/revision identities still resolve. If they
do not, retain the copied database as archival evidence and build a fresh sidecar.

### Ollama models

The validated path is to provision the same Ollama runtime family and pull the exact
model tags before enforcing offline operation:

```powershell
ollama pull embeddinggemma
ollama pull gemma3:4b
```

These commands contact the model registry and therefore require explicit operator
authorization. Repository agents must not run them implicitly.

For an air-gapped destination, preserve approved installers and model artifacts on
controlled media. Direct migration of the internal `.ollama\models` directory is not
yet a certified Recoll Next procedure. If attempted, treat it as a version-specific
experiment and validate model hashes/details and live inference before claiming
Level A fidelity.

## Phase 5 — restore on the destination

1. Verify transfer-media hashes before opening the capsule.
2. Restore/clone source into a new explicit destination directory.
3. Confirm the expected commit and mandatory documents.
4. Recreate `.venv`; do not copy it.
5. Install and configure Recoll under a destination profile.
6. Rewrite every `topdirs` and `dbdir` path.
7. Install/start Ollama and verify exact models.
8. Restore or rebuild Xapian according to the selected strategy.
9. Restore or rebuild the semantic sidecar.
10. Keep the source and rollback capsule untouched until acceptance.

When creating a working tree from the local bundle, ensure any automatically
configured bundle-origin path remains local metadata. The repository contract still
prohibits fetch, pull, push, and remote contact.

## Phase 6 — rebuild derived indexes

Validate Recoll configuration paths before indexing:

```powershell
& 'C:\Program Files\Recoll\recollindex.exe' -c DESTINATION_CONFIG -E
```

Run ordinary indexing only after checking the resolved `dbdir` is the intended new
destination. A full reset (`-z`) is destructive to the selected index and is not a
routine portability command.

Then create a scoped semantic store. Start with a small, representative query:

```powershell
python src\semantic\recoll_ai.py sync `
  --store .local\migration-sample.sqlite3 `
  --confdir DESTINATION_CONFIG `
  --query "mime:application/pdf" `
  --timeout 120 `
  --batch-size 32
```

Use a separate store for independently managed scopes. If multiple partial queries
share one store, understand `--keep-missing` before the second sync.

## Phase 7 — acceptance

### Source and governance

```powershell
git status --short
git log -1 --format="%H %s"
python src\semantic\rclsem_ledger.py verify governance\events.jsonl
python -W error::ResourceWarning -m unittest discover -s tests\semantic
```

Expected commit and ledger head must match the manifest. A clean working tree is the
default; list intentional destination configuration separately.

### Recoll/Xapian

- Profile path validation succeeds.
- Index status has no unexplained errors.
- Representative exact terms, phrases, MIME filters, and path scopes find known
  documents.
- Open-source actions resolve to destination files.

### Ollama and semantic retrieval

```powershell
python src\semantic\recoll_ai.py doctor
python src\semantic\recoll_ai.py search `
  --store .local\migration-sample.sqlite3 `
  --limit 3 `
  "representative concept"
```

Confirm source identifiers, paths, offsets, finite scores, and model dimensions.

### Cited answers and memory

```powershell
python src\semantic\recoll_ai.py ask `
  --store .local\migration-sample.sqlite3 `
  --evidence-limit 2 `
  --timeout 600 `
  --view summary `
  "Summarize the representative evidence."

python src\semantic\recoll_ai.py memory-search `
  --store .local\migration-sample.sqlite3 `
  "representative evidence"
```

Check that every final citation resolves to supplied primary evidence and that the
remembered interpretation appears only as secondary memory.

### GUI

```powershell
python src\semantic\recoll_ai_gui.py `
  --store .local\migration-sample.sqlite3
```

Exercise Concept Search, one AI view, cancellation, evidence opening, and Markdown
export. Native UI Level B additionally requires a rebuilt Recoll binary with the AI
dock.

### Runtime ledgers

Verify each selected runtime ledger individually and compare its head with the
manifest. A newly rebuilt sidecar may legitimately start a new operational chain;
record that discontinuity instead of pretending continuity.

## Phase 8 — close or roll back

Accept only the fidelity levels that passed. Record deviations and retained rollback
locations. If a derived layer fails, preserve it for diagnosis and rebuild into a new
path. Never repair a failed hash chain by editing JSON Lines, and never overwrite the
source machine's only accepted Xapian or SQLite database.

