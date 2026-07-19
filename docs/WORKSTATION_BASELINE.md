# Verified workstation baseline

## Purpose

This file records the development machine state observed on 2026-07-19 in the
Asia/Calcutta timezone. It is evidence for migration planning, not a requirement
that future machines reproduce every path or version exactly.

## Host and runtime

| Component | Observed value | Validation |
| --- | --- | --- |
| Operating system | Microsoft Windows NT 10.0.26200.0 | PowerShell/.NET environment |
| Repository path | `G:\GPTWORKFLOW\recoll` | Current working directory |
| Git | 2.54.0.windows.1 | `git --version` |
| Project Python | 3.14.0 | `.venv\Scripts\python.exe --version` |
| Recoll-bundled Python | 3.12.4 | bundled `python.exe --version` |
| SQLite through project Python | 3.50.4 | Python `sqlite3.sqlite_version` |
| Tk | 8.6 | Python `tkinter.TkVersion` |
| Recoll | 1.43.5 | `recollindex -h` version footer |
| Xapian | 1.4.25 | `recollindex -h` version footer |
| Ollama | 0.32.1 | `ollama --version` |
| CMake | Not installed/on `PATH` | command discovery failed |
| qmake | Not installed/on `PATH` | command discovery failed |

The Recoll Python bridge exists because the project Python and Recoll extension ABI
differ. The current discovery path is:

```text
C:\Program Files\Recoll\Share\filters\python\python.exe
```

Do not copy that absolute path into product defaults. The bridge discovers the
installed Recoll location or accepts `--recoll-python`/`RECOLL_PYTHON`.

## Active local model inventory

The live doctor check reported:

| Role | Model | Observed details |
| --- | --- | --- |
| Chat/generation | `gemma3:4b` | 4.3B, `Q4_K_M` |
| Embedding | `embeddinggemma:latest` | 307.58M, `BF16`, 768 dimensions validated |

The active endpoint is `http://127.0.0.1:11434` and passes the local-only policy.
The local Ollama model store occupied approximately 3.689 GiB at observation time.

## Active Recoll profile

The Windows profile is located at:

```text
C:\Users\ambij\AppData\Local\Recoll
```

Material configuration:

```text
dbdir = D:/recoll_windex
topdirs = multiple F:, G:, and H: corpus roots
```

At observation time Recoll reported:

```text
dbtotdocs = 144253
filesdone = 100744
fileerrors = 0
hasmonitor = 0
```

The Xapian directory contained seven Glass database files totalling approximately
8.194 GiB. The exact `topdirs` list is machine-private configuration and must be
captured from `recoll.conf` during migration, then mapped deliberately on the
destination.

## Repository and derived data footprint

| Path | Approximate size | Portability class |
| --- | ---: | --- |
| Repository including `.git` | 0.147 GiB | Source capsule |
| `.git` | 0.084 GiB | Source-history capsule |
| `.local` | 0.014 GiB | Derived semantic/runtime capsule |
| `D:\recoll_windex` | 8.194 GiB | Derived lexical capsule |
| Ollama models | 3.689 GiB | Model-runtime capsule |

`.local` is ignored by Git and currently contains semantic SQLite stores, runtime
JSONL ledgers, lock files, and local process logs. It is not included in a Git bundle.

## Verified functionality

- `recoll_ai.py doctor` reached loopback Ollama and found both required models.
- Recoll inventory bridging worked through the bundled Python runtime.
- `embeddinggemma` returned 768-dimensional vectors.
- The academic sidecar contains a previously synchronized PDF sample.
- Semantic search and a cited `gemma3:4b` answer were live-validated.
- Perspective Memory table creation and query embedding were live-validated.
- The Tk 8.6 AI Perspective companion launched successfully.
- The semantic automated suite currently has 63 passing tests.
- The native Qt AI dock is source-complete but not compiled on this machine.

## Known portability gaps

- There is no locked Python dependency manifest because the active Python path uses
  the standard library; the superseded Chroma prototype has separate unpinned
  dependencies and should not define the product environment.
- The native Windows C++/Qt build is not reproducible here until CMake and a matching
  compiler/Qt/Xapian development SDK are installed.
- Direct air-gapped copying of the Ollama internal model store is not yet certified.
- A copied Xapian database may retain source paths that differ on the destination.
- Rebuilding Xapian can change `rcludi`, requiring semantic and perspective rebuilds.
- Exact semantic cosine search scans all stored segments and is not yet suitable for
  the full 144,253-document inventory without an acceleration layer.
