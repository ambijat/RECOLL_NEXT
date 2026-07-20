# Semantic retrieval

## Purpose

This artifact connects Recoll's authoritative document inventory to the versioned
SQLite semantic sidecar and retrieves evidence with local Ollama embeddings. It is a
readable reference implementation for the semantic face of prismatic search. It does
not replace Recoll lexical search.

## Source contract

`rclsem_recoll.py` imports `recoll.recoll` only when inventory enumeration begins.
If the current interpreter has no compatible binding, it discovers the Python
runtime bundled by the Windows Recoll installer and starts
`rclsem_recoll_bridge.py`. The bridge streams private JSON lines over a local child
process pipe; it creates no intermediate document files and contacts no network.

The adapter runs `mime:*` with `fetchtext=True` by default and maps each result as
follows:

| Recoll field | Semantic field | Rule |
| --- | --- | --- |
| `rcludi` | `document_id` | Required stable identity |
| `text` | `text` | Extracted local content; bytes decode as UTF-8 with replacement |
| `title` | `title` | Optional evidence label |
| `url`, then `filename` | `path` | Source locator fallback |

The adapter deliberately has no import-time Recoll dependency. Unit tests can use a
fake connector. `--recoll-python` or the `RECOLL_PYTHON` environment variable can
override runtime discovery when Recoll is installed in a nonstandard location.

## Retrieval contract

`rclsem_retrieve.py` embeds the query with the same model namespace used at indexing
time, rejects vector-dimension drift, and calculates cosine similarity against every
stored segment. Results sort by descending similarity and then by SHA-256 segment ID,
making ties reproducible.

Every result carries the document ID, source revision, segment ID, title, path,
character offsets, segment text, and cosine score. These fields form the evidence
boundary required for later hybrid ranking and cited answers.

Exact scanning is intentional for this checkpoint: it provides an easily audited
correctness oracle. A future approximate index may accelerate candidate generation,
but regression tests must compare it against this reference path.

## Commands

From the repository root:

```powershell
python src\semantic\recoll_ai.py sync --store .local\semantic.sqlite3
```

Run default Prismatic search with local Ollama:

```powershell
python src\semantic\recoll_ai.py search --store .local\semantic.sqlite3 `
  "integrity of cited evidence" --limit 10
```

Or run authoritative Exact search with no semantic store or Ollama dependency:

```powershell
python src\semantic\recoll_ai.py search --mode exact `
  "integrity of cited evidence" --limit 10
```

The endpoint, embedding model, Recoll configuration directory, segmentation sizes,
batch size, result limit, ledger path, and session identifier are configurable. The
Ollama endpoint remains loopback-only under the current policy.

Unless `--ledger` is supplied, each command writes lifecycle events beside the store
at `<store>.events.jsonl`. Query text is represented only by its SHA-256 digest.
Document bodies, segment text, paths, and exception messages are excluded from event
payloads.

## Current validation

The semantic suite has 48 passing tests, including inventory mapping, bridge protocol
validation, source evidence,
deterministic tie handling, dimension mismatch rejection, and privacy-safe query
events. A live bridge check from the Python 3.14 virtual environment read a real
Recoll document through Recoll's bundled Python 3.12 binding. A live synthetic search
through `embeddinggemma` returned 768-dimensional vectors and ranked the governance
document first for `integrity of cited evidence`.

## Hybrid boundary

`rclsem_hybrid.py` now combines bounded authoritative Recoll candidates and exact
semantic results concurrently. Exact preserves Recoll order, Prismatic uses
configurable weighted reciprocal-rank fusion with lexical-only fallback, and
Conceptual accepts a vector hit only after its identity and revision resolve against
live Recoll. All results expose their contributing channels and source ranks.
