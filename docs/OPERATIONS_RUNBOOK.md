# Local operations runbook

## Daily startup

From the repository root:

```powershell
.\.venv\Scripts\Activate.ps1
python src\semantic\recoll_ai.py doctor
python src\semantic\rclsem_ledger.py verify governance\events.jsonl
git status --short
```

The doctor must report loopback policy and the selected models. A dirty tree is not
automatically wrong, but identify ownership before editing overlapping files.

## Recoll indexing

Recoll indexing precedes semantic synchronization. The active profile defines corpus
roots in `topdirs` and Xapian output in `dbdir`. Use the Recoll GUI or installed
`recollindex` for lexical indexing; do not make the AI subsystem crawl the filesystem
as a competing inventory.

Before a long semantic sync:

- let the selected Recoll indexing pass finish;
- confirm expected files are searchable in ordinary Recoll;
- start with a narrow Recoll query and a dedicated store;
- ensure Ollama is ready;
- ensure destination disk space and timeout are adequate.

Recoll's `idxstatus.txt` is operational status, not a ledger or durable source of
truth. Inspect it through the selected profile directory.

## Semantic synchronization

Repository-document example:

```powershell
python src\semantic\recoll_ai.py sync `
  --store .local\project-docs.sqlite3 `
  --query "mime:text/markdown" `
  --timeout 120 `
  --batch-size 4 `
  --max-runtime 900
```

Academic PDF example:

```powershell
python src\semantic\recoll_ai.py sync `
  --store .local\booklibrandom-pdfs.sqlite3 `
  --query "dir:BOOKLIBRANDOM mime:application/pdf" `
  --timeout 120 `
  --batch-size 4 `
  --max-runtime 1800
```

The query is executed by Recoll/Xapian. Validate it in ordinary Recoll first.

The synchronizer reports added, updated, unchanged, deleted documents, and embedded
segments. An immediate unchanged second pass should embed zero segments.

### Partial-scope warning

By default, documents already in the selected semantic namespace but absent from the
current query are deleted after successful enumeration. Prefer one store per managed
scope. Use `--keep-missing` only when deliberately accumulating several partial
queries into one store and plan explicit stale cleanup.

### Long runs

Embedding thousands of segments can run for a long time. Use bounded sample stores
before full-corpus work. `--timeout` bounds each Ollama request; `--max-runtime` is
checked between those bounded requests. The index-builder GUI additionally terminates
its owned child at the configured total limit. `--progress` emits privacy-safe document
and batch stages to stderr without changing JSON stdout. Cancellation may leave
already committed documents intact; atomic replacement protects the document being
written, and stale deletion is skipped when enumeration/embedding fails.

## Semantic search

```powershell
python src\semantic\recoll_ai.py search `
  --store .local\booklibrandom-pdfs.sqlite3 `
  --limit 5 `
  "the conceptual question"
```

Current search is exact cosine over every stored segment. It is reference-correct but
not yet accelerated for the complete Recoll inventory.

## Cited AI perspectives

```powershell
python src\semantic\recoll_ai.py ask `
  --store .local\booklibrandom-pdfs.sqlite3 `
  --view decisions `
  --evidence-limit 2 `
  --timeout 600 `
  "What decisions are supported and why?"
```

Views: `answer`, `summary`, `timeline`, `contradictions`, `decisions`, and `actions`.
Generation can be slow on CPU. The answer must cite exact supplied segment IDs; an
invented, malformed, supported-but-uncited response is rejected.

Supported cited answers are stored in Perspective Memory by default. Add
`--no-remember` for ephemeral or sensitive analysis. Questions and generated answers
remain local but are present in the SQLite database when remembered.

## Perspective Memory

```powershell
python src\semantic\recoll_ai.py memory-search `
  --store .local\booklibrandom-pdfs.sqlite3 `
  --limit 5 `
  "decisions about local retrieval"
```

Only memories whose cited segment, document, and source revision still resolve are
returned. Memory is not yet automatically inserted into new prompts.

## Runnable desktop GUI

```powershell
python src\semantic\recoll_ai_gui.py `
  --store .local\booklibrandom-pdfs.sqlite3
```

The companion provides Concept Search, cited views, cancellation, evidence opening,
and Markdown export. It runs backend operations as child processes. Closing or
cancelling the GUI operation must not stop ordinary Recoll search.

The native Qt dock is present in source but requires a locally compiled Recoll binary
or future package. The currently installed Recoll binary does not acquire source
changes automatically.

## JSON automation boundary

Add `--json` to `sync`, `search`, `ask`, `memory-search`, or `doctor` for stable
machine-readable output. Pass arguments as a process argument vector. Do not compose
private queries into a shell command string or log them indiscriminately.

## Backup

Back up capsules independently:

- source through a clean local Git bundle or cold repository copy;
- governance ledger with source history;
- corpus through private backup policy;
- Recoll profile as configuration;
- Xapian only as a complete cold database or by rebuilding;
- semantic store and runtime ledger only after stopping writers;
- model inventory as version/tag records plus approved installation artifacts.

Verify hashes and ledger heads. Do not treat `.lock`, PID, status, cache, `.venv`, or
build products as irreplaceable evidence.

## Recovery principles

| Failure | Safe response |
| --- | --- |
| Ollama unavailable | Keep using Exact Recoll search; start/repair Ollama, rerun doctor |
| Required model missing | Provision exact configured model with explicit authorization |
| Recoll binding unavailable | Use discovered bundled bridge or explicit matching `--recoll-python` |
| Ollama timeout | Reduce evidence/batch scope, increase bounded timeout, preserve cancellation |
| Empty semantic results | Confirm store, namespace/model, sync query, and document count |
| Vector dimension mismatch | Select correct model/namespace or rebuild; never coerce vectors |
| Stale Perspective Memory | Resync primary documents; stale memory remains suppressed |
| SQLite incompatibility/corruption | Preserve failed file and rebuild into a new path |
| Xapian failure | Preserve database, validate profile/version, prefer rebuild from corpus |
| Ledger verification failure | Preserve file; diagnose first bad line; never edit/repair silently |
| GUI appears frozen | Allow long model timeout or cancel child operation; ordinary Recoll remains separate |
| `ask` rejected by parser | Confirm current source exposes `ask` in `recoll_ai.py --help` |

## Privacy operations

- Keep Ollama on loopback unless a governed policy explicitly changes.
- Do not add corpus, `.local`, runtime ledgers, exported answers, or environment dumps
  to Git.
- Treat semantic stores as sensitive: they contain extracted segments, paths,
  embeddings, questions, and generated perspectives.
- Runtime ledgers contain identifiers and metrics, not full bodies or prompts.
- Project governance events contain architectural summaries, not private machine
  inventories or corpus paths.

## End-of-session checkpoint

```powershell
python -W error::ResourceWarning -m unittest discover -s tests\semantic
python src\semantic\rclsem_ledger.py verify governance\events.jsonl
git diff --check
git status --short
git log -3 --oneline
```

Update `SESSION_START.md` when state, milestone, risks, or mandatory operating rules
changed. Commit locally only. Never fetch, pull, push, or open a remote PR.
