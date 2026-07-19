# Configuration and storage reference

## Configuration precedence

Recoll configuration and Recoll Next AI configuration are separate layers.

- Recoll profile selection uses explicit `--confdir` where available, otherwise the
  Recoll binding's default profile resolution. `RECOLL_CONFDIR` is understood by the
  native Recoll programs.
- AI CLI settings use explicit command-line arguments and compiled defaults.
- The native Qt AI dock uses its `RECOLL_AI_*` environment variables for development
  and packaged path discovery.
- The Tk companion accepts `--store` and `--query`; its controls can change the store
  interactively.

Absolute workstation paths are examples, never product constants.

## Recoll profile

The material `recoll.conf` settings are:

| Setting | Purpose | Migration rule |
| --- | --- | --- |
| `topdirs` | Corpus roots indexed by Recoll | Map and existence-check every root |
| `dbdir` | Xapian database directory | Set an explicit destination path |
| `skippedPaths` | Excluded paths | Preserve intent and review destination syntax |

Use a separate configuration directory for an independent profile. Pass it to
Recoll commands with `-c PATH`, to the AI synchronizer with `--confdir PATH`, or set
`RECOLL_CONFDIR` for native Recoll processes.

The semantic layer opens Xapian only through Recoll's supported Python API. It does
not parse or edit Glass files directly.

## AI defaults

| Setting | Default | Scope |
| --- | --- | --- |
| Ollama endpoint | `http://127.0.0.1:11434` | All AI CLI operations |
| Embedding model | `embeddinggemma` | Doctor, sync, search, ask, memory search |
| Chat model | `gemma3:4b` | Doctor and ask |
| Inventory query | `mime:*` | Sync |
| Sync timeout | 30 seconds | Per Ollama request client |
| Search timeout | 30 seconds | Query embedding request |
| Ask timeout | 120 seconds CLI default | Embedding and generation client |
| Sync batch size | 32 | Segment embeddings |
| Segment target | 900 characters | Deterministic segmenter |
| Segment overlap | 150 characters | Deterministic segmenter |
| Search limit | 10 | Semantic evidence results |
| Ask evidence limit | 6 | Primary segments in generation context |
| Memory-search limit | 5 | Prior perspective results |
| Ask memory | Enabled for supported cited answers | Disable with `--no-remember` |

The runnable GUI deliberately uses tighter evidence limits and a longer workstation
generation timeout: five search results, two answer evidence segments, and 600
seconds for `ask`. These values belong to the presentation contract and must remain
visible and configurable as packaging matures.

## CLI reference

All semantic commands are rooted at:

```powershell
python src\semantic\recoll_ai.py COMMAND
```

### `doctor`

Checks endpoint policy, connectivity, and required model inventory. Options:
`--endpoint`, `--embedding-model`, `--chat-model`, `--timeout`, and `--json`.

### `sync`

Enumerates a Recoll query, segments changed documents, embeds them, replaces each
document atomically, and removes stale documents only after successful enumeration.

Required: `--store`. Configuration: `--endpoint`, `--embedding-model`, `--timeout`,
`--ledger`, `--session`, `--confdir`, `--query`, `--recoll-python`, `--batch-size`,
`--target-chars`, `--overlap-chars`, `--keep-missing`, and `--json`.

`--keep-missing` prevents deletion of sidecar documents absent from the current
query. Use it when synchronizing several partial scopes into one store; otherwise a
later narrow query could delete records from an earlier scope.

### `search`

Embeds the query and performs deterministic exact cosine ranking over the selected
semantic namespace. Required: `--store` and positional query. Optional shared
settings plus `--limit`/`-n`.

### `ask`

Retrieves primary evidence and asks the local chat model for schema-constrained
output. Required: `--store` and positional query. It supports `answer`, `summary`,
`timeline`, `contradictions`, `decisions`, and `actions` views. Additional options:
`--chat-model`, `--evidence-limit`, and `--no-remember`.

### `memory-search`

Embeds a query and retrieves prior validated AI perspectives whose primary citations
still resolve to a current semantic source revision. Required: `--store` and
positional query. Optional shared settings plus `--limit`/`-n`.

### Shared output and ledger options

`--json` is the stable machine boundary used by both GUIs. Without it, output is for
humans. Runtime ledger defaults to `<store>.events.jsonl`; `--ledger` overrides the
path, and `--session` supplies a correlation identifier.

## Environment variables

| Variable | Consumer | Meaning |
| --- | --- | --- |
| `RECOLL_CONFDIR` | Native Recoll tools | Selected Recoll profile directory |
| `RECOLL_PYTHON` | Semantic Recoll adapter | Python executable containing matching `recoll.recoll` |
| `RECOLL_AI_PYTHON` | Native AI dock | Project/backend Python executable |
| `RECOLL_AI_SCRIPT` | Native AI dock | Absolute or packaged path to `recoll_ai.py` |
| `RECOLL_AI_WORKDIR` | Native AI dock | Child-process working directory |
| `RECOLL_AI_STORE` | Native AI dock | Default semantic SQLite sidecar |

Do not use environment dumps as diagnostics because they may contain unrelated
secrets. Record only selected, non-sensitive values needed to reproduce a run.

## SQLite sidecar

The file given by `--store` currently contains two independently derived layers.

### Semantic index tables

- `store_metadata` — schema version, currently `1`.
- `semantic_namespaces` — embedding model, segmenter version, dimensions, creation.
- `semantic_documents` — `rcludi`, revision, transitional title/path cache, counts.
- `semantic_segments` — stable identity, offsets, transitional text, packed float32
  embedding.

Namespaces are deterministically keyed by embedding model and segmenter version.
Dimensions are learned once and then enforced.

### Perspective Memory tables

- `perspective_namespaces` — embedding model and fixed dimensions.
- `ai_perspectives` — content-addressed question, validated answer, view, model,
  citation provenance, timestamp, and packed float32 embedding.

Perspective retrieval verifies cited segment/document/revision triples against the
semantic tables. A missing or changed primary record suppresses the memory.

SQLite content is private local data. Questions, extracted text, paths, embeddings,
and generated answers may be present even though `.local` is Git-ignored.

## Event ledgers

The versioned project chain is `governance/events.jsonl`. Each semantic profile uses
a separate runtime chain, normally `<store>.events.jsonl`. Sibling `.lock` files are
coordination bytes, not evidence.

Verify any chain with:

```powershell
python src\semantic\rclsem_ledger.py verify PATH_TO_LEDGER
```

Never merge JSONL ledgers by concatenation, reformat them, or edit earlier events.

## Local-only endpoint policy

The Ollama adapter accepts loopback endpoints by default. A non-loopback host is a
privacy boundary change, not routine configuration. It requires explicit policy,
documentation, tests, and governance approval. No agent may infer authorization to
send corpus content to a remote model from the mere presence of an endpoint.

