# Recoll Next — restart capsule

This file is the operational handoff for the session that follows the Xapian-first
hybrid retrieval milestone. Read it immediately after `SESSION_START.md`. The tracked
contracts remain authoritative; this document records the exact stopping point and
the safest order for resuming work.

## Resume anchor

- Product implementation anchor: `ad45283a887ff1e8a9bad560194fce31fb5516dd`
  (`Implement Xapian-first hybrid retrieval`).
- Project ledger at that milestone: 26 events.
- Verified ledger head:
  `396fa010deaedd374b03006a75659fa10fc3bd4021a5c848eea0edd14dd4ff5d`.
- Restart-capsule governance event: sequence 27, head
  `3f98757f719a9071292de73e187f586317b0bbfabfcffdfdf4895e3f626231e3`.
- Semantic test suite: 81 tests passing.
- No Git remote operation was performed or authorized.
- The user-supplied `RecollNext-Audit-and-Development-Pathway.md` is intentionally
  untracked and untouched. A cold directory copy will carry it; a Git bundle will
  not.

The commit containing this restart capsule may be newer than the product anchor.
Always inspect `git log -1 --oneline` and `git status --short`; do not reset a newer
local commit merely to reproduce the anchor above.

## What is complete

The active search boundary is Xapian-first:

- **Exact** sends the query to Recoll, preserves its document order, and requires no
  semantic SQLite store or Ollama process.
- **Prismatic** retrieves bounded lexical and semantic candidates concurrently,
  deduplicates at document level, and combines ranks using configurable weighted
  reciprocal-rank fusion. A semantic failure produces an explicit lexical fallback.
- **Conceptual** performs exact cosine search over the semantic sidecar, then accepts
  a result only when its `rcludi` resolves to the same live Recoll source revision.
- Results expose retrieval mode, channel provenance, original lexical/semantic ranks,
  similarity where applicable, and fusion score where applicable.
- Query events retain only a SHA-256 query digest. Document bodies and raw prompts do
  not enter the ledger.
- The CLI, Tk companion, and native Qt source expose all three modes.
- The old Chroma entry points and `rclsem_talk.py` are loud retirement tombstones;
  they contain no active Chroma pipeline.

Primary implementation files:

- `src/semantic/rclsem_hybrid.py`
- `src/semantic/rclsem_recoll.py`
- `src/semantic/rclsem_recoll_bridge.py`
- `src/semantic/recoll_ai.py`
- `src/semantic/recoll_ai_gui.py`
- `src/qtgui/aiperspective_w.{h,cpp}`
- `tests/semantic/test_hybrid_retrieval.py`

## Last verified evidence

The complete semantic suite passed:

```powershell
$env:PYTHONPATH='src/semantic'
python -m unittest discover -s tests/semantic
```

Expected summary: `Ran 81 tests` and `OK`.

Store-free Exact search succeeded against the active Recoll profile:

```powershell
python src/semantic/recoll_ai.py search --mode exact --json --limit 3 "recoll"
```

Live Prismatic search also completed. For the query `governance`, four semantic
candidates from `.local/semantic.sqlite3` failed the live revision gate and were
correctly rejected; current lexical evidence was still returned. This demonstrates
correct safety behavior, but it also means that store should be resynchronized before
using it as the representative relevance baseline.

The project ledger verified as:

```json
{"event_count":26,"head_hash":"396fa010deaedd374b03006a75659fa10fc3bd4021a5c848eea0edd14dd4ff5d"}
```

That is the product-milestone anchor. After recording this restart capsule, the
expected current chain is 27 events with head
`3f98757f719a9071292de73e187f586317b0bbfabfcffdfdf4895e3f626231e3`.

## Known limitations that remain

1. The repository environment uses Python 3.14 while the installed Recoll 1.43.5
   binding is for Python 3.12.4. The private bundled-Python bridge works on the
   validated workstation; general Windows discovery and packaging remain open.
2. An older native `ENABLE_SEMANTIC` route can still reach the retired
   `rclsem_talk.py` tombstone. Remove that build/runtime route before the first native
   Qt compilation, and record the architecture change in the project ledger.
3. The native Qt AI dock is source- and contract-tested but has not been compiled on
   the baseline workstation because the matching Qt/C++ SDK is absent.
4. First generation with `gemma3:4b` was approximately 107 seconds. Exact and lexical
   fallback avoid that latency, but generation performance itself is unchanged.
5. The semantic sidecar still duplicates extracted segment text, title, and path.
   These are transitional caches, not authoritative data.
6. Same-workstation portability passed source, lexical, AI, and event fidelity. A
   physical second-machine and cross-OS proof remain outstanding.
7. A fresh `ad45283a` audit package has not been created. The existing audit ZIP under
   `.local` belongs to the older `d9500690` checkpoint and must not be represented as
   proof of the hybrid milestone.

## Immediate next course

Proceed in this order unless the user explicitly changes priorities.

### 1. Freeze the `ad45283a` audit baseline

Create a new local source bundle and manifest without contacting a remote. Prove:

- the full 26-event chain verifies from genesis;
- event 21 reproduces old head
  `4a4386257d1c7ca484ea8aeec608926fba463ef1cbf148df70e6bd35d81adf08`;
  confirm the same value independently from the old audit manifest rather than
  trusting this handoff alone;
- event 26 terminates at `396fa010...ff5d`;
- `d9500690` is an ancestor of `ad45283a` and the range contains five commits;
- the new bundle digest matches its manifest;
- an isolated clone resolves exactly to `ad45283a`, is clean, and passes 81 tests;
- Exact succeeds in an isolated environment where no sidecar path exists;
- Prismatic rejects a deliberately stale copied fixture while returning lexical
  evidence; and
- every retirement tombstone exits with its explicit message without importing
  Chroma.

Do not rename or mutate the user's live sidecar for this proof. Use an isolated clone,
copied fixture, and temporary runtime ledger.

### 2. Remove the obsolete native semantic route

Remove the `ENABLE_SEMANTIC` path that launches `rclsem_talk.py`, while preserving the
supported AI Perspective dock. Add static/build-contract tests, update the component
catalog and session briefing, append an `architecture.decision.*` or milestone event,
verify the ledger, and commit locally. Do not delete the tombstones until compatibility
policy explicitly permits it.

### 3. Establish the relevance baseline

Add a versioned evaluation schema and harness. Keep private corpus queries and graded
judgments under `.local/evaluation/` by default; version only the schema, sanitized
fixtures, and a content-hash manifest. Stratify queries into at least known-item,
phrase-precise, conceptual, and paraphrase groups. Measure recall@10 and nDCG@10
while sweeping:

- lexical-to-semantic weight ratios from `2:1` through `1:2`;
- RRF `k` in `{10, 60, 100}`; and
- per-channel candidate depth in `{20, 50, 100}`.

Operate on a copied store and send runtime events to a temporary ledger. Hash the
source bundle and original store before and after so the benchmark cannot silently
mutate its baseline.

### 4. Resynchronize, measure, then deduplicate

Resynchronize a copied representative semantic store before collecting the accepted
baseline. Record size, document/segment counts, query latency, stale rejection rate,
recall@10, and nDCG@10. Only then migrate away duplicated title, path, and segment
text.

The schema invariant for text removal is:

> Evidence text may be presented only when live Recoll resolution by `rcludi`, source
> revision, offsets, and reconstructed segment identity all agree. Any mismatch
> excludes the semantic item from evidence and records a resynchronization need.
> Offset-drifted cached text and metadata-only records must never be treated as valid
> citations.

Prefer a schema-versioned disposable rebuild over a complicated in-place migration.
Repeat the unchanged relevance benchmark after deduplication so size, latency, and
quality differences remain attributable.

## First commands in the next session

From the repository root:

```powershell
Get-Content -Raw SESSION_START.md
Get-Content -Raw docs/PORTABILITY_CONTRACT.md
Get-Content -Raw docs/AGENT_HANDOFF.md
Get-Content -Raw RESUME_NEXT_SESSION.md
git status --short
git log -1 --oneline
python src/semantic/rclsem_ledger.py verify governance/events.jsonl
$env:PYTHONPATH='src/semantic'
python -m unittest discover -s tests/semantic
```

These commands establish identity and integrity; complete every remaining document
under **Required reading** in `SESSION_START.md` before any mutation.

Then confirm local runtime readiness without changing any model or store:

```powershell
python src/semantic/recoll_ai.py doctor --json --timeout 3
python src/semantic/recoll_ai.py search --mode exact --json --limit 3 "recoll"
```

Do not fetch, pull, push, contact a Git remote, install dependencies, synchronize a
store, or run a migration until the tracked contracts have been read and the user has
placed that action in scope.

## Flash-drive transfer checklist

A copied project directory is a valid cold source capsule only if hidden `.git` data,
tracked files, and intentional untracked files are all preserved. Before copying:

1. Close editors or processes writing inside the repository.
2. If copying ignored SQLite stores or ledgers under `.local`, stop their writers and
   copy complete SQLite files and any required companions according to
   `docs/DATA_MIGRATION.md`; never copy a live partial WAL set.
3. Record `git status --short`, the current commit, ledger head, and SHA-256 hashes of
   material capsules.
4. Keep the audit report identified as an intentional untracked file.
5. Safely eject the flash drive after the copy completes.

The repository directory alone does **not** necessarily carry:

- source documents located on other drives;
- the active Recoll profile or its configured Xapian `dbdir`;
- compatible Recoll binaries and Python bindings;
- Ollama itself or its installed model blobs; or
- a portable Python environment.

Do not rely on a copied `.venv` on another machine. Recreate it locally with:

```powershell
python src/semantic/initsemenv.py .venv --verify
```

On the destination, remap corpus/profile paths, rebuild Xapian when compatibility is
uncertain, provision exact Ollama models through an approved local/offline method,
and validate each portability fidelity level separately. The authoritative procedures
are `docs/PORTABILITY_CONTRACT.md`, `docs/DATA_MIGRATION.md`, and
`docs/TRANSFER_MANIFEST_TEMPLATE.md`.

## Completion discipline

For every resumed milestone:

1. preserve the untracked audit report and unrelated user changes;
2. run focused tests, then the full semantic suite;
3. run `git diff --check`;
4. verify the project ledger before and after appending a governed event;
5. update `SESSION_START.md` and this restart capsule if state or priorities change;
6. commit only the intended files locally; and
7. report remaining limitations honestly, especially native Qt compilation and
   physical second-machine portability.
