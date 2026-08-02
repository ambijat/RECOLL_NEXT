# Recoll Next — restart capsule

This file is the operational handoff for the source-publication-readiness checkpoint.
Read it immediately after `SESSION_START.md`. The tracked contracts remain
authoritative; this document records the exact stopping point and the safest order for
resuming work.

## Resume anchor

- Verified source publication anchor: `af461ea4`
  (`Prepare local source publication checkpoint`).
- Project ledger at the publication milestone: 33 events.
- Verified ledger head:
  `8633a8279073e00c72b89c032d665a313100b783e2e8e84cf191f05b3d6a263c`.
- Source-publication policy is sequence 32; the verified local-readiness milestone is
  sequence 33 at the head above.
- Semantic test suite: 98 tests passing under Python 3.14 with resource warnings
  treated as errors.
- No Git remote had been contacted at the source-readiness checkpoint. The user later
  authorized initial publication of the selected product branch only to
  `https://github.com/ambijat/RECOLL_NEXT.git`; governance event 34 records the narrow
  exception and all broader remote operations remain denied.
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
- The obsolete `ENABLE_SEMANTIC` build option, `DocSequenceSem` C++ worker, jsoncpp
  dependency, and Qt simple-search mode are removed. The supported AI Perspective
  dock remains wired through `recoll_ai.py --json`; tombstones remain only for older
  installed callers.
- Cited-answer structured output enumerates only the supplied segment IDs, while the
  independent validator still rejects any unknown or missing required citation.
- The Tk presentation is split into an everyday evidence/interpretation workspace and
  a separate semantic index builder. Progress, bounded total runtime, safe
  cancellation, and selected-evidence revalidation are covered by the shared CLI
  contract and tests.
- Public-source onboarding now includes the brochure, quick start, contribution and
  security policies, changelog, GPL notice, strengthened ignore rules, and a local
  publication checklist. Private runtime/data/model artifacts remain excluded.

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

Expected summary: `Ran 98 tests` and `OK`.

Store-free Exact search succeeded against the active Recoll profile:

```powershell
python src/semantic/recoll_ai.py search --mode exact --json --limit 3 "recoll"
```

Live Prismatic search also completed. For the query `governance`, four semantic
candidates from `.local/semantic.sqlite3` failed the live revision gate and were
correctly rejected; current lexical evidence was still returned. This demonstrates
correct safety behavior, but it also means that store should be resynchronized before
using it as the representative relevance baseline.

The project ledger's source-publication milestone verified with 33 events and head
`8633a8279073e00c72b89c032d665a313100b783e2e8e84cf191f05b3d6a263c`.
Historical heads remain independently readable in `governance/CHECKPOINTS.md`.

## Known limitations that remain

1. The repository environment uses Python 3.14 while the installed Recoll 1.43.5
   binding is for Python 3.12.4. The private bundled-Python bridge works on the
   validated workstation; general Windows discovery and packaging remain open.
2. The native Qt AI dock is source- and contract-tested but has not been compiled on
   the baseline workstation because the matching Qt/C++ SDK is absent.
3. First generation with `gemma3:4b` was approximately 107 seconds. Exact and lexical
   fallback avoid that latency, but generation performance itself is unchanged.
4. The semantic sidecar still duplicates extracted segment text, title, and path.
   These are transitional caches, not authoritative data.
5. Same-workstation portability passed source, lexical, AI, and event fidelity. A
   physical second-machine and cross-OS proof remain outstanding.
6. A fresh `41696e1e` audit package has not been created. The existing audit ZIP under
   `.local` belongs to the older `d9500690` checkpoint and must not be represented as
   proof of the hybrid milestone.
7. The active workstation Recoll profile resolves repository content from the
   predecessor `recoll` working tree. Relevance work must use a deliberately scoped
   current profile rather than treating those stale repository results as evidence.

## Immediate next course

Proceed in this order unless the user explicitly changes priorities.

### 1. Preserve the local publication checkpoint

Verify the final local commit, 98-test suite, public-product documentation links,
ignore behavior, and project ledger from genesis. Keep the intentional audit report
untracked and all private `.local` capsules ignored. Publication may use only the exact
destination and operation recorded by governance event 34.

### 2. Establish the relevance baseline

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

### 3. Resynchronize, measure, then deduplicate

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
placed that exact action and destination in scope. Publication authorization never
implies permission for other remote operations.

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
