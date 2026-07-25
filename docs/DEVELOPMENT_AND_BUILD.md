# Development, build, and test guide

## Supported working boundary

The validated development surface is Windows PowerShell with an installed Recoll
runtime, local Ollama, a repository Python virtual environment, and the Tk companion.
The source also retains the inherited C++/Qt build system, but the native dock has not
yet been compiled on the current workstation.

Commands in this guide run from the repository root unless stated otherwise. They do
not authorize any Git remote or cloud-model operation.

## Source layout

| Location | Responsibility |
| --- | --- |
| `AGENTS.md` | Mandatory repository and agent rules |
| `SESSION_START.md` | Current milestone, state, risks, and required reading |
| `docs/` | Product contracts, references, runbooks, and handoff documentation |
| `governance/` | Versioned project hash chain and externalized checkpoints |
| `src/semantic/` | Local Ollama, segmentation, storage, retrieval, answers, memory, CLI, and Tk GUI |
| `src/qtgui/aiperspective_w.*` | Native Qt AI Perspective dock |
| `src/qtgui/rclmain_w.*` | Main-window integration for the dock |
| `tests/semantic/` | Fast dependency-free product contract tests |
| `.local/` | Ignored runtime stores, ledgers, and logs; never assumed present in Git |
| `.venv/` | Ignored workstation Python environment; recreate on each machine |
| Remaining `src/` directories | Inherited Recoll engine, extraction, query, and UI source |

## Python environment

The active rebuilt subsystem uses the Python standard library. It does not require
the legacy `chromadb` or Python `ollama` packages: HTTP calls use the local adapter in
`rclsem_ollama.py`, and storage uses `sqlite3`.

Create a clean environment on Windows with a selected installed Python:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
python -m unittest discover -s tests\semantic
```

The dependency-free cross-platform bootstrap performs the environment creation
without contacting a package index or model registry:

```powershell
python src\semantic\initsemenv.py .venv --verify
```

It deliberately does not install Recoll, Ollama, Python packages, or models. Those
remain separately authorized workstation-provisioning steps.

Python 3.14.0 is the verified project runtime. Do not infer that copying its `.venv`
to another machine is supported. If a different Python is selected, run the full
suite and record the version in the transfer manifest.

On POSIX systems the equivalent activation path is `.venv/bin/activate`; the rebuilt
Windows workflow is validated, while POSIX portability still requires live testing.

### Recoll binding ABI

The project interpreter may be unable to import `recoll.recoll` because compiled
extensions are tied to a Python ABI. `rclsem_recoll.py` handles this on Windows by
launching `rclsem_recoll_bridge.py` under Recoll's bundled Python and streaming
private JSON Lines through a local pipe.

Discovery order:

1. explicit `--recoll-python`;
2. `RECOLL_PYTHON` environment variable;
3. `ProgramFiles\Recoll\Share\filters\python\python.exe`;
4. `ProgramFiles(x86)` equivalent.

The bridge must match the destination Recoll installation. Never solve the ABI
mismatch by copying a compiled Recoll Python extension into an unrelated interpreter.

## Ollama runtime

Install Ollama through an operator-approved local installer, then install the exact
models declared by the profile. Network installation or model pulling is an explicit
machine-provisioning step and is not authorized automatically by repository work.

Validate after provisioning:

```powershell
ollama --version
ollama list
python src\semantic\recoll_ai.py doctor
```

Current defaults are `embeddinggemma`, `gemma3:4b`, and loopback endpoint
`http://127.0.0.1:11434`. All remain configurable.

## Automated tests

Run the complete rebuilt-product suite:

```powershell
python -W error::ResourceWarning -m unittest discover -s tests\semantic
```

Run focused tests while developing:

```powershell
python -m unittest tests.semantic.test_ollama_client
python -m unittest tests.semantic.test_semantic_sync
python -m unittest tests.semantic.test_semantic_retrieval
python -m unittest tests.semantic.test_cited_answer
python -m unittest tests.semantic.test_perspective_memory
python -m unittest tests.semantic.test_ai_perspective_gui
python -m unittest tests.semantic.test_event_ledger
python -m unittest tests.semantic.test_project_governance
```

Compile-check Python sources:

```powershell
python -m compileall -q src\semantic
```

Verify documentation patches and repository integrity:

```powershell
git diff --check
python src\semantic\rclsem_ledger.py verify governance\events.jsonl
git status --short
```

Unit tests use fake model and Recoll adapters and therefore do not prove a live
workstation is configured. A stable checkpoint also runs `doctor`, a bounded live
embedding operation, and—when generation changed—one cited local answer.

## Native C++/Qt build

The experimental CMake build requires at least CMake 3.25. The source declares Qt
5.15+ or Qt 6.4+, a C++17 compiler in the current configuration, and development
packages for Xapian, LibXml2, LibXslt, Zlib, Iconv, plus either libmagic or a suitable
`find` command. Qt GUI builds additionally select Core and the components listed in
`src/qtgui/CMakeLists.txt`; WebEngine is enabled by default.

Key CMake options:

```text
RECOLL_QTGUI=ON
RECOLL_QT6_BUILD=ON
RECOLL_ENABLE_WEBENGINE=ON
RECOLL_ENABLE_X11MON=OFF
RECOLL_ENABLE_LIBMAGIC=OFF
RECOLL_ENABLE_SYSTEMD=ON on Linux
```

A generic out-of-tree configuration is:

```text
cmake -S . -B build-local -DRECOLL_QTGUI=ON -DRECOLL_QT6_BUILD=ON
cmake --build build-local --parallel
```

This command is documentary on the current workstation: CMake, qmake, and a matching
Qt/C++ development SDK are absent. A future Windows build must record compiler, Qt,
Xapian, CMake, generator, configuration options, and produced binary hashes before
claiming Level B portability.

The AI dock sources are already included in both CMake and qmake source lists. A build
acceptance run must verify the dock's View-menu toggle, query handoff, asynchronous
child process, cancellation, source opening, and lack of interference with ordinary
Recoll search.

## Retired semantic prototype

The inherited Chroma implementation has been retired. `rclsem_common.py`,
`rclsem_embed.py`, and `rclsem_query.py` remain only as small failure tombstones so an
older caller receives actionable migration guidance instead of an optional-package
import error. No active or tombstone module imports `chromadb` or the Python `ollama`
package.

New work uses `recoll_ai.py`, `rclsem_ollama.py`, `rclsem_store.py`, and the tested
modules linked from `SESSION_START.md`. `initsemenv.py` replaces the downloading,
POSIX-only bootstrap. The older native `ENABLE_SEMANTIC`/`DocSequenceSem` route and
its jsoncpp build dependency have been removed. The supported native integration is
the AI Perspective dock consuming the shared `recoll_ai.py --json` boundary; Python
tombstones remain only to guide already-installed legacy callers.

## Build and dependency change control

When adding a non-standard Python dependency, compiler requirement, database
extension, or runtime service:

1. justify why the standard-library/local boundary is insufficient;
2. add a pinned, reviewable dependency manifest;
3. document offline acquisition and license/provenance implications;
4. test a clean environment rather than an upgraded existing `.venv`;
5. update the portability contract and workstation baseline; and
6. record the architectural decision in the governance ledger.
